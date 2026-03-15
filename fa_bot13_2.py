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

    def on_hand_start(self, game_info: GameInfo, current_state: PokerState) -> None:
        self.equity_cache = {}

    def on_hand_end(self, game_info: GameInfo, current_state: PokerState) -> None:
        self.hands_played += 1
        if current_state.payoff > 0 and not current_state.opp_revealed_cards:
            self.opp_folds += 1

    def calc_equity(self, hole_cards, board_cards, iters):
        state_key = (tuple(hole_cards), tuple(board_cards))
        if state_key in self.equity_cache:
            return self.equity_cache[state_key]

        deck = eval7.Deck()
        hole = [eval7.Card(c) for c in hole_cards]
        board = [eval7.Card(c) for c in board_cards]

        for card in hole + board:
            deck.cards.remove(card)

        score = 0
        for _ in range(iters):
            deck.shuffle()
            draw_count = 5 - len(board)
            draw = deck.peek(draw_count)
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
        card1, card2 = hole_cards[0], hole_cards[1]

        r1 = rank_values[card1[0]]
        r2 = rank_values[card2[0]]
        s1 = card1[1]
        s2 = card2[1]

        high = max(r1, r2)
        low = min(r1, r2)
        is_suited = s1 == s2
        is_pair = high == low

        if is_pair:
            return 0.52 + (high - 2) * 0.025

        equity = 0.40 + (high - 2) * 0.012 + (low - 2) * 0.004
        if is_suited:
            equity += 0.04

        gap = high - low
        if gap == 1:
            equity += 0.03
        elif gap == 2:
            equity += 0.02
        elif gap > 4:
            equity -= 0.06

        return min(equity, 0.85)

    def get_move(
        self, game_info: GameInfo, current_state: PokerState
    ) -> ActionFold | ActionCall | ActionCheck | ActionRaise | ActionBid:

        if current_state.street == "pre-flop":
            equity = self.get_preflop_equity(current_state.my_hand)
        else:
            iters = (
                150
                if current_state.street == "flop"
                else (75 if current_state.street == "turn" else 30)
            )
            if game_info.time_bank < 4.0:
                iters = 10
            equity = self.calc_equity(current_state.my_hand, current_state.board, iters)

        if current_state.opp_revealed_cards:
            equity += 0.08

        if current_state.street == "auction":
            if equity > 0.65:
                bid_amt = min(int(current_state.pot * 1.5), current_state.my_chips)
            else:
                bid_amt = min(int(current_state.pot * 0.1), current_state.my_chips)
            return ActionBid(bid_amt)

        can_raise = current_state.can_act(ActionRaise)
        can_check = current_state.can_act(ActionCheck)

        cost_to_call = current_state.cost_to_call
        pot_size = current_state.pot
        prev_pot = max(1, pot_size - cost_to_call)
        pot_odds = (
            cost_to_call / (pot_size + cost_to_call)
            if (pot_size + cost_to_call) > 0
            else 0
        )

        if current_state.street == "pre-flop":
            if cost_to_call > 40 and equity < 0.62:
                return ActionFold()
            if cost_to_call > 150 and equity < 0.72:
                return ActionFold()
            if cost_to_call > 400 and equity < 0.82:
                return ActionFold()
            if cost_to_call > 1000 and equity < 0.85:
                return ActionFold()

        if current_state.street != "pre-flop":
            our_val = eval7.evaluate(
                [eval7.Card(c) for c in current_state.my_hand + current_state.board]
            )
            hand_type = eval7.handtype(our_val)

            suits = [c[1] for c in current_state.board]
            if len(suits) > 0:
                max_suit_count = max(suits.count(s) for s in set(suits))
                if max_suit_count >= 3 and hand_type not in [
                    "Flush",
                    "Full House",
                    "Quads",
                    "Straight Flush",
                ]:
                    equity -= 0.15

            if cost_to_call > 100 or (prev_pot > 0 and cost_to_call > prev_pot * 0.4):
                if hand_type == "High Card":
                    equity = min(equity, 0.20)
                elif hand_type == "Pair":
                    equity = min(equity, 0.45)
                elif hand_type == "Two Pair":
                    equity = min(equity, 0.60)
                elif hand_type == "Three of a Kind":
                    equity = min(equity, 0.75)
                elif hand_type == "Straight":
                    equity = min(equity, 0.85)

            if cost_to_call > 1000:
                if hand_type in ["High Card", "Pair", "Two Pair", "Three of a Kind"]:
                    return ActionFold()

        if prev_pot > 0:
            bet_ratio = cost_to_call / prev_pot
            if bet_ratio > 1.5:
                equity -= 0.15
            elif bet_ratio > 0.75:
                equity -= 0.08

        if equity > 0.70 and can_raise:
            if cost_to_call > 300 and equity < 0.85:
                return ActionCall()

            # 1. THE TRAP DOOR: If we have an absolute monster (>92% win chance),
            # there is a 35% chance we just check to let the opponent try to bluff us.
            if equity > 0.92 and current_state.street in ["flop", "turn"] and can_check:
                if random.random() < 0.35:
                    return ActionCheck()

            min_raise, max_raise = current_state.raise_bounds

            if equity > 0.90:
                fraction = random.uniform(0.40, 0.75)

            elif equity > 0.80:
                fraction = random.uniform(0.80, 1.30)

            else:
                fraction = random.uniform(0.50, 0.80)

            # fraction = (random.uniform(0.7, 1.2) if equity > 0.85 else random.uniform(0.4, 0.7))
            raise_amt = int(pot_size * fraction)
            return ActionRaise(max(min_raise, min(raise_amt, max_raise)))

        call_threshold = max(pot_odds + 0.05, 0.40)
        if pot_odds > 0.40:
            call_threshold = max(call_threshold, 0.60)

        if equity > call_threshold:
            if can_check:
                return ActionCheck()
            return ActionCall()

        fold_freq = self.opp_folds / max(1, self.hands_played)
        bluff_chance = 0.20 if (fold_freq > 0.45 and self.hands_played > 10) else 0.08

        if (
            can_raise
            and current_state.street in ["flop", "turn"]
            and can_check
            and pot_size < 300
        ):
            if random.random() < bluff_chance:
                min_raise, max_raise = current_state.raise_bounds
                return ActionRaise(max(min_raise, min(int(pot_size * 0.4), max_raise)))

        if can_check:
            return ActionCheck()
        return ActionFold()


if __name__ == "__main__":
    run_bot(Player(), parse_args())
