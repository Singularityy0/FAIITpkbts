import random

import eval7

from pkbot.actions import ActionBid, ActionCall, ActionCheck, ActionFold, ActionRaise
from pkbot.base import BaseBot
from pkbot.runner import parse_args, run_bot
from pkbot.states import GameInfo, PokerState


class Player(BaseBot):
    def __init__(self) -> None:
        self.equity_cache = {}
        self.hands_played = 0
        self.opp_folds = 0
        self.heavy_bets_faced = 0
        self.mode = "BULLY"

    def on_hand_start(self, game_info: GameInfo, current_state: PokerState) -> None:
        self.equity_cache = {}

        if self.hands_played > 12:
            aggr_ratio = self.heavy_bets_faced / self.hands_played
            if aggr_ratio > 0.55:
                self.mode = "TRAP"
            else:
                self.mode = "BULLY"

    def on_hand_end(self, game_info: GameInfo, current_state: PokerState) -> None:
        self.hands_played += 1
        if current_state.payoff > 0 and not current_state.opp_revealed_cards:
            self.opp_folds += 1

    def calc_equity(self, hole_cards, board_cards, opp_revealed, iters):
        state_key = (tuple(hole_cards), tuple(board_cards), tuple(opp_revealed))
        if state_key in self.equity_cache:
            return self.equity_cache[state_key]

        deck = eval7.Deck()
        hole = [eval7.Card(c) for c in hole_cards]
        board = [eval7.Card(c) for c in board_cards]
        revealed = [eval7.Card(c) for c in opp_revealed]

        for card in hole + board + revealed:
            deck.cards.remove(card)

        score = 0
        for _ in range(iters):
            deck.shuffle()
            draw_count = 5 - len(board)
            draw = deck.peek(draw_count)

            if len(revealed) == 1:
                opp_hole = revealed + [deck.cards[draw_count]]
            elif len(revealed) == 2:
                opp_hole = revealed
            else:
                opp_hole = deck.cards[draw_count : draw_count + 2]

            our_val = eval7.evaluate(hole + board + draw)
            opp_val = eval7.evaluate(opp_hole + board + draw)

            if our_val > opp_val:
                score += 2
            elif our_val == opp_val:
                score += 1

        equity = score / (2 * iters)
        self.equity_cache[state_key] = equity
        return equity

    def get_preflop_equity(self, hole_cards):
        rank_vals = {
            "2": 2,
            "3": 3,
            "4": 4,
            "5": 5,
            "6": 6,
            "7": 7,
            "8": 8,
            "9": 9,
            "T": 10,
            "J": 11,
            "Q": 12,
            "K": 13,
            "A": 14,
        }
        r1, r2 = rank_vals[hole_cards[0][0]], rank_vals[hole_cards[1][0]]
        high, low = max(r1, r2), min(r1, r2)
        is_suited = hole_cards[0][1] == hole_cards[1][1]

        if high == low:
            return 0.52 + (high - 2) * 0.025
        equity = 0.40 + (high - 2) * 0.012 + (low - 2) * 0.004
        if is_suited:
            equity += 0.04
        if (high - low) == 1:
            equity += 0.03
        return min(equity, 0.85)

    def get_move(
        self, game_info: GameInfo, current_state: PokerState
    ) -> ActionFold | ActionCall | ActionCheck | ActionRaise | ActionBid:
        opp_revealed = (
            current_state.opp_revealed_cards if current_state.opp_revealed_cards else []
        )
        cost = current_state.cost_to_call
        pot = current_state.pot

        if cost > pot * 0.5 or cost > 150:
            self.heavy_bets_faced += 1

        if current_state.street == "pre-flop":
            raw_eq = self.get_preflop_equity(current_state.my_hand)
        else:
            iters = (
                250
                if current_state.street == "flop"
                else (120 if current_state.street == "turn" else 60)
            )
            if game_info.time_bank < 5.0:
                iters = 20
            raw_eq = self.calc_equity(
                current_state.my_hand, current_state.board, opp_revealed, iters
            )

        can_raise = current_state.can_act(ActionRaise)
        can_check = current_state.can_act(ActionCheck)
        pot_odds = cost / (pot + cost) if (pot + cost) > 0 else 0

        if current_state.street == "auction":
            if self.mode == "TRAP":
                bid_amt = min(
                    int(pot * 1.61 if raw_eq > 0.65 else pot * 0.1),
                    current_state.my_chips,
                )
            else:
                bid_amt = min(
                    int(pot * 2.2 if raw_eq > 0.65 else pot * 0.15),
                    current_state.my_chips,
                )
            return ActionBid(bid_amt)

        if current_state.street == "pre-flop":
            if cost > 100 and raw_eq < 0.60:
                return ActionFold()
            if cost > 400 and raw_eq < 0.78:
                return ActionFold()

        adj_eq = raw_eq

        if current_state.street != "pre-flop":
            my_cards = [eval7.Card(c) for c in current_state.my_hand]
            board_cards = [eval7.Card(c) for c in current_state.board]
            all_cards = my_cards + board_cards

            our_val = eval7.evaluate(all_cards)
            h_type = eval7.handtype(our_val)

            board_ranks = sorted([c.rank for c in board_cards])
            my_ranks = sorted([c.rank for c in my_cards], reverse=True)
            max_board_rank = max(board_ranks) if board_ranks else 0

            board_suits = [c.suit for c in board_cards]
            max_suit_count = (
                max(board_suits.count(s) for s in set(board_suits))
                if board_suits
                else 0
            )
            is_paired_board = len(set(board_ranks)) < len(board_ranks)

            if self.mode == "TRAP":
                if h_type == "High Card":
                    adj_eq = min(adj_eq, 0.15)
                elif h_type == "Pair":
                    if my_ranks[0] < max_board_rank and my_ranks[1] < max_board_rank:
                        adj_eq = min(adj_eq, 0.35)
                    else:
                        adj_eq = min(adj_eq, 0.60)
                elif h_type == "Two pair":
                    if is_paired_board:
                        adj_eq = min(adj_eq, 0.50)
                    else:
                        adj_eq = min(adj_eq, 0.75)
                elif h_type == "Three of a kind":
                    if is_paired_board:
                        adj_eq = min(adj_eq, 0.65)
                    else:
                        adj_eq = min(adj_eq, 0.85)
                elif h_type == "Straight":
                    if my_ranks[0] < board_ranks[-1]:
                        adj_eq = min(adj_eq, 0.50)

                if max_suit_count >= 3 and h_type not in [
                    "Flush",
                    "Full House",
                    "Four of a kind",
                    "Straight Flush",
                ]:
                    adj_eq -= 0.20

                if cost > 0:
                    bet_ratio = cost / (pot - cost) if (pot - cost) > 0 else 1.0
                    if bet_ratio > 1.2:
                        adj_eq -= 0.15
                    elif bet_ratio > 0.7:
                        adj_eq -= 0.08

                if adj_eq < 0.85:
                    if cost > pot * 0.6 and adj_eq < 0.65:
                        return ActionFold()
                    if cost > 600 and adj_eq < 0.80:
                        return ActionFold()

            else:
                if cost > 100 or (pot > cost and cost > (pot - cost) * 0.4):
                    if h_type == "High Card":
                        adj_eq = min(adj_eq, 0.20)
                    elif h_type == "Pair":
                        adj_eq = min(adj_eq, 0.45)
                if current_state.opp_revealed_cards:
                    adj_eq += 0.12

        if adj_eq > 0.90 and can_check and current_state.street in ["flop", "turn"]:
            if random.random() < 0.45:
                return ActionCheck()

        if cost > 0 and adj_eq > 0.92 and can_raise:
            min_r, max_r = current_state.raise_bounds
            raise_amt = int(pot * random.uniform(2.0, 3.5))
            return ActionRaise(max(min_r, min(raise_amt, max_r)))

        if adj_eq > 0.70 and can_raise:
            if cost > 300 and adj_eq < 0.85:
                return ActionCall()

            min_r, max_r = current_state.raise_bounds

            if self.mode == "BULLY":
                if adj_eq > 0.92:
                    fraction = random.choice(
                        [random.uniform(0.40, 0.70), random.uniform(1.5, 2.5)]
                    )
                elif adj_eq > 0.82:
                    fraction = random.uniform(1.0, 1.8)
                else:
                    fraction = random.uniform(0.60, 1.1)
            else:
                if adj_eq > 0.92:
                    fraction = random.uniform(0.40, 0.70)
                elif adj_eq > 0.82:
                    fraction = random.uniform(0.80, 1.20)
                else:
                    fraction = random.uniform(0.50, 0.80)

            return ActionRaise(max(min_r, min(int(pot * fraction), max_r)))

        if adj_eq > (pot_odds + 0.05):
            return ActionCheck() if can_check else ActionCall()

        fold_freq = self.opp_folds / max(1, self.hands_played)
        bluff_chance = 0.28 if (fold_freq > 0.40 and self.hands_played > 10) else 0.10

        if (
            can_raise
            and current_state.street in ["flop", "turn"]
            and can_check
            and pot < 400
        ):
            if random.random() < bluff_chance:
                min_r, max_r = current_state.raise_bounds
                bluff_fraction = random.choice([0.45, 1.25])
                return ActionRaise(max(min_r, min(int(pot * bluff_fraction), max_r)))

        return ActionCheck() if can_check else ActionFold()


if __name__ == "__main__":
    run_bot(Player(), parse_args())
