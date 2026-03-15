import random

import eval7

from pkbot.actions import ActionBid, ActionCall, ActionCheck, ActionFold, ActionRaise
from pkbot.base import BaseBot
from pkbot.runner import parse_args, run_bot
from pkbot.states import GameInfo, PokerState


class Player(BaseBot):
    def __init__(self) -> None:
        self.equity_cache = {}

    def on_hand_start(self, game_info: GameInfo, current_state: PokerState) -> None:
        self.equity_cache = {}

    def on_hand_end(self, game_info: GameInfo, current_state: PokerState) -> None:
        pass

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
        rank_values = {
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
        r1, r2 = rank_values[hole_cards[0][0]], rank_values[hole_cards[1][0]]
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

        if current_state.street == "pre-flop":
            equity = self.get_preflop_equity(current_state.my_hand)
        else:
            iters = (
                250
                if current_state.street == "flop"
                else (120 if current_state.street == "turn" else 60)
            )
            if game_info.time_bank < 5.0:
                iters = 15
            equity = self.calc_equity(
                current_state.my_hand, current_state.board, opp_revealed, iters
            )

        if current_state.street == "auction":
            bid_amt = min(
                int(
                    current_state.pot * 2.2
                    if equity > 0.62
                    else current_state.pot * 0.05
                ),
                current_state.my_chips,
            )
            return ActionBid(bid_amt)

        can_raise, can_check = (
            current_state.can_act(ActionRaise),
            current_state.can_act(ActionCheck),
        )
        cost_to_call, pot_size = current_state.cost_to_call, current_state.pot
        pot_odds = (
            cost_to_call / (pot_size + cost_to_call)
            if (pot_size + cost_to_call) > 0
            else 0
        )

        if current_state.street == "pre-flop":
            if cost_to_call > 120 and equity < 0.66:
                return ActionFold()
            if cost_to_call > 450 and equity < 0.82:
                return ActionFold()

        if current_state.street != "pre-flop":
            our_val = eval7.evaluate(
                [eval7.Card(c) for c in current_state.my_hand + current_state.board]
            )
            hand_type = eval7.handtype(our_val)
            board_ranks = sorted([eval7.Card(c).rank for c in current_state.board])
            my_ranks = sorted(
                [eval7.Card(c).rank for c in current_state.my_hand], reverse=True
            )
            kicker = my_ranks[0]

            if hand_type == "High Card":
                equity = min(equity, 0.18)
            elif hand_type == "Pair":
                if kicker < max(board_ranks):
                    equity = min(equity, 0.40)
                else:
                    equity = min(equity, 0.62)
            elif hand_type == "Two pair":
                equity = min(equity, 0.74)
            elif hand_type == "Three of a kind":
                equity = min(equity, 0.86)
            elif hand_type == "Straight":
                if kicker < board_ranks[-1]:
                    equity = min(equity, 0.48)

            if cost_to_call > 0:
                bet_ratio = (
                    cost_to_call / (pot_size - cost_to_call)
                    if (pot_size - cost_to_call) > 0
                    else 1.0
                )
                if bet_ratio > 1.2:
                    equity -= 0.18
                elif bet_ratio > 0.6:
                    equity -= 0.10

            if cost_to_call > 600 and equity < 0.84:
                return ActionFold()

        if equity > 0.74 and can_raise:
            if cost_to_call > 300 and equity < 0.90:
                return ActionCall()
            min_raise, max_raise = current_state.raise_bounds
            fraction = (
                random.uniform(0.9, 1.4) if equity > 0.88 else random.uniform(0.6, 0.9)
            )
            return ActionRaise(max(min_raise, min(int(pot_size * fraction), max_raise)))

        if equity > (pot_odds + 0.10):
            return ActionCheck() if can_check else ActionCall()

        if (
            can_raise
            and current_state.street in ["flop", "turn"]
            and can_check
            and pot_size < 450
        ):
            if random.random() < 0.18:
                min_raise, max_raise = current_state.raise_bounds
                return ActionRaise(max(min_raise, min(int(pot_size * 0.5), max_raise)))

        return ActionCheck() if can_check else ActionFold()


if __name__ == "__main__":
    run_bot(Player(), parse_args())
