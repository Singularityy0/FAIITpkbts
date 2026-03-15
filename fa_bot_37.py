import base64
import json
import random
import zlib

import eval7

from pkbot.actions import ActionBid, ActionCall, ActionCheck, ActionFold, ActionRaise
from pkbot.base import BaseBot
from pkbot.runner import parse_args, run_bot
from pkbot.states import GameInfo, PokerState


class Player(BaseBot):
    def __init__(self) -> None:
        self.encoded_payload = b"eJx1U8lqwzAQ/RedTdAWLb2VQgiUktCm5+BitTYYqSg2OZT+e9UeonFnfNV7zFtm9MX2w0f/0ObufLqmU4rh/Bo/2yGHjt3xjbLbhhXgWF5Igtvahu3mcdyn+RJulOON4J1u2CGGvwnP7RDf0hXAmosqgGErXFMdPqWYJmTRKTxhYdE67AASjPMlQ5rz4f3+cYgd8iE2vEj0OYQ1RlGRsAeMe12KeplyW8JMdBIn1D8ZmiZrHNy35lCHiutl6WM3zpeenu+1qhNWebgT6jy88NUsqWZ+Q8PyiRPyHhwBFUkZs7KghRnlcHMLL9asZAJmpMA/AhwslxUmA1stwYLI0rj7/gE0UjjT"
        self.flop_equities = json.loads(
            zlib.decompress(base64.b64decode(self.encoded_payload)).decode("utf-8")
        )
        self.hands_played = 0
        self.opp_folds = 0
        self.heavy_bets_faced = 0
        self.stack_losses = 0
        self.net_chips = 0
        self.mode = "BULLY"
        self.equity_cache = {}

    def on_hand_start(self, game_info: GameInfo, current_state: PokerState) -> None:
        self.equity_cache = {}
        if self.hands_played > 10:
            fold_ratio = self.opp_folds / max(1, self.hands_played)
            aggr_ratio = self.heavy_bets_faced / max(1, self.hands_played)
            if self.net_chips < -1500 or self.stack_losses >= 2:
                self.mode = "SAFE"
            elif (
                0.35 < fold_ratio < 0.55
                and 0.35 < aggr_ratio < 0.55
                and self.hands_played > 40
            ):
                self.mode = "CFR_CRUSHER"
            elif aggr_ratio > 0.45:
                self.mode = "ANTI_MANIAC"
            elif fold_ratio < 0.25 and aggr_ratio < 0.30:
                self.mode = "VALUE_TOWN"
            else:
                self.mode = "BULLY"

    def on_hand_end(self, game_info: GameInfo, current_state: PokerState) -> None:
        self.hands_played += 1
        self.net_chips += current_state.payoff
        if current_state.payoff > 0 and len(current_state.opp_revealed_cards) < 2:
            self.opp_folds += 1
        if current_state.payoff < -1200:
            self.stack_losses += 1

    def get_abstract_state(self, hole_cards, board_cards):
        my_cards = [eval7.Card(c) for c in hole_cards]
        board = [eval7.Card(c) for c in board_cards]
        suits = [c.suit for c in board]
        max_suit = max([suits.count(s) for s in set(suits)]) if suits else 0
        suit_str = (
            "Monotone" if max_suit == 3 else "TwoTone" if max_suit == 2 else "Rainbow"
        )
        ranks = sorted([c.rank for c in board])
        paired_str = (
            "Paired"
            if (
                ranks
                and len(ranks) >= 3
                and (ranks[0] == ranks[1] or ranks[1] == ranks[2])
            )
            else "Unpaired"
        )
        our_val = eval7.evaluate(my_cards + board)
        h_type = eval7.handtype(our_val).split()[0]
        if h_type == "Two":
            h_type = "TwoPair"
        if h_type == "High":
            h_type = "HighCard"
        if h_type == "Three":
            h_type = "ThreeOfAKind"
        return f"{h_type}_{suit_str}_{paired_str}"

    def calc_equity(self, hole_cards, board_cards, opp_revealed, iters):
        state_key = (tuple(hole_cards), tuple(board_cards), tuple(opp_revealed))
        if state_key in self.equity_cache:
            return self.equity_cache[state_key]
        deck = eval7.Deck()
        hole = [eval7.Card(c) for c in hole_cards]
        board = [eval7.Card(c) for c in board_cards]
        revealed = [eval7.Card(c) for c in opp_revealed]
        for card in hole + board + revealed:
            try:
                deck.cards.remove(card)
            except ValueError:
                pass
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
        r1, r2 = hole_cards[0][0], hole_cards[1][0]
        s1, s2 = hole_cards[0][1], hole_cards[1][1]
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
        val1, val2 = rank_vals[r1], rank_vals[r2]
        high, low = max(val1, val2), min(val1, val2)
        gap = high - low
        equity = 0.45 + (high * 0.01) + (low * 0.005)
        if s1 == s2:
            equity += 0.035
        if gap == 1:
            equity += 0.025
        elif gap == 2:
            equity += 0.015
        return min(max(equity, 0.35), 0.85)

    def get_move(self, game_info: GameInfo, current_state: PokerState):
        opp_revealed = (
            current_state.opp_revealed_cards if current_state.opp_revealed_cards else []
        )
        cost = current_state.cost_to_call
        pot = current_state.pot
        can_raise = current_state.can_act(ActionRaise)
        can_check = current_state.can_act(ActionCheck)

        if cost > pot * 0.5 or cost > 150:
            self.heavy_bets_faced += 1

        if current_state.street == "pre-flop":
            raw_eq = self.get_preflop_equity(current_state.my_hand)
        elif current_state.street in ["flop", "auction"]:
            state_key = self.get_abstract_state(
                current_state.my_hand, current_state.board
            )
            if state_key in self.flop_equities:
                raw_eq = self.flop_equities[state_key]
            else:
                iters = 100 if game_info.time_bank > 5.0 else 20
                raw_eq = self.calc_equity(
                    current_state.my_hand, current_state.board, opp_revealed, iters
                )
        else:
            iters = 120 if current_state.street == "turn" else 60
            if game_info.time_bank < 5.0:
                iters = 20
            raw_eq = self.calc_equity(
                current_state.my_hand, current_state.board, opp_revealed, iters
            )

        if current_state.street == "auction":
            if raw_eq > 0.65:
                bid_amt = min(int(pot * 1.5), current_state.my_chips)
                bid_amt = min(bid_amt, 400)
            elif raw_eq > 0.45:
                bid_amt = min(int(pot * 0.45), current_state.my_chips)
            else:
                bid_amt = min(int(pot * 0.1), current_state.my_chips)
            return ActionBid(max(0, bid_amt))

        if current_state.street == "pre-flop":
            if cost > 40 and raw_eq < 0.62:
                return ActionFold()
            if cost > 150 and raw_eq < 0.72:
                return ActionFold()
            if cost > 400 and raw_eq < 0.82:
                return ActionFold()
            if cost > 1000 and raw_eq < 0.85:
                return ActionFold()

        adj_eq = raw_eq
        if current_state.street != "pre-flop":
            my_cards = [eval7.Card(c) for c in current_state.my_hand]
            board_cards = [eval7.Card(c) for c in current_state.board]
            our_val = eval7.evaluate(my_cards + board_cards)
            h_type = eval7.handtype(our_val).lower()
            suits = [c.suit for c in board_cards]
            if suits:
                max_suit_count = max(suits.count(s) for s in set(suits))
                if max_suit_count >= 3 and h_type not in [
                    "flush",
                    "full house",
                    "four of a kind",
                    "straight flush",
                ]:
                    adj_eq -= 0.15

            if cost > 100:
                if h_type == "high card":
                    adj_eq = min(adj_eq, 0.20)
                elif h_type == "pair":
                    adj_eq = min(adj_eq, 0.45)
                elif h_type == "two pair":
                    adj_eq = min(adj_eq, 0.60)

            if cost > 1000 and h_type in [
                "high card",
                "pair",
                "two pair",
                "three of a kind",
            ]:
                return ActionFold()

        pot_odds = cost / (pot + cost) if (pot + cost) > 0 else 0

        if adj_eq > 0.70 and can_raise:
            if cost > 200 and adj_eq < 0.96 and self.mode != "ANTI_MANIAC":
                return ActionCall()
            min_r, max_r = current_state.raise_bounds
            if adj_eq > 0.85:
                fraction = random.uniform(0.7, 1.2)
            else:
                fraction = random.uniform(0.4, 0.7)
            raise_amt = int(pot * fraction)
            return ActionRaise(max(min_r, min(raise_amt, max_r)))

        call_threshold = max(pot_odds + 0.05, 0.40)
        if pot_odds > 0.40:
            call_threshold = max(call_threshold, 0.60)

        if adj_eq > call_threshold:
            return ActionCheck() if can_check else ActionCall()

        if (
            can_raise
            and current_state.street in ["flop", "turn"]
            and can_check
            and pot < 300
        ):
            fold_freq = self.opp_folds / max(1, self.hands_played)
            bluff_chance = (
                0.20 if (fold_freq > 0.45 and self.hands_played > 10) else 0.08
            )
            if random.random() < bluff_chance:
                min_r, max_r = current_state.raise_bounds
                return ActionRaise(max(min_r, min(int(pot * 0.4), max_r)))

        return ActionCheck() if can_check else ActionFold()


if __name__ == "__main__":
    run_bot(Player(), parse_args())
