"""
GTO Poker Bot — Sneak Peek Hold'em
Combines:
  - O(1) preflop equity lookup (complete 169-hand table)
  - O(1) flop abstract state lookup (compressed Monte Carlo payload)
  - Board texture analysis & danger factor system
  - Empirical river win rates
  - Opponent modeling with adaptive modes
  - GTO-inspired balanced bet sizing & mixed strategies
  - Smart auction bidding based on information value
"""

import base64
import json
import random
import zlib

import eval7

from pkbot.actions import ActionBid, ActionCall, ActionCheck, ActionFold, ActionRaise
from pkbot.base import BaseBot
from pkbot.runner import parse_args, run_bot
from pkbot.states import GameInfo, PokerState

STARTING_STACK = 5000
BIG_BLIND = 20

MONSTER_HANDS = {"straight flush", "four of a kind", "full house"}
STRONG_HANDS = {"flush", "straight", "three of a kind"}
MEDIUM_HANDS = {"two pair"}
WEAK_HANDS = {"pair", "high card"}

BET_SMALL = 0.33
BET_MEDIUM = 0.55
BET_LARGE = 0.75
BET_OVERBET = 1.10


class Player(BaseBot):
    """GTO-inspired poker bot for Sneak Peek Hold'em."""

    def __init__(self) -> None:
        self._flop_payload = b"eJx1U8lqwzAQ/RedTdAWLb2VQgiUktCm5+BitTYYqSg2OZT+e9UeonFnfNV7zFtm9MX2w0f/0ObufLqmU4rh/Bo/2yGHjt3xjbLbhhXgWF5Igtvahu3mcdyn+RJulOON4J1u2CGGvwnP7RDf0hXAmosqgGErXFMdPqWYJmTRKTxhYdE67AASjPMlQ5rz4f3+cYgd8iE2vEj0OYQ1RlGRsAeMe12KeplyW8JMdBIn1D8ZmiZrHNy35lCHiutl6WM3zpeenu+1qhNWebgT6jy88NUsqWZ+Q8PyiRPyHhwBFUkZs7KghRnlcHMLL9asZAJmpMA/AhwslxUmA1stwYLI0rj7/gE0UjjT"
        self.flop_equities: dict[str, float] = json.loads(
            zlib.decompress(base64.b64decode(self._flop_payload)).decode()
        )

        self.preflop_equity: dict[str, float] = {
            "AA": 0.85, "KK": 0.82, "QQ": 0.80, "JJ": 0.77, "TT": 0.75,
            "99": 0.72, "88": 0.69, "77": 0.66, "66": 0.63, "55": 0.60,
            "44": 0.57, "33": 0.54, "22": 0.51,
            "AKs": 0.67, "AQs": 0.66, "AJs": 0.65, "ATs": 0.64,
            "A9s": 0.62, "A8s": 0.61, "A7s": 0.60, "A6s": 0.59,
            "A5s": 0.60, "A4s": 0.59, "A3s": 0.58, "A2s": 0.57,
            "AKo": 0.65, "AQo": 0.63, "AJo": 0.62, "ATo": 0.61,
            "A9o": 0.58, "A8o": 0.57, "A7o": 0.56, "A6o": 0.55,
            "A5o": 0.55, "A4o": 0.54, "A3o": 0.53, "A2o": 0.52,
            "KQs": 0.64, "KJs": 0.63, "KTs": 0.62, "K9s": 0.60,
            "K8s": 0.58, "K7s": 0.57, "K6s": 0.56, "K5s": 0.55,
            "K4s": 0.54, "K3s": 0.53, "K2s": 0.52,
            "KQo": 0.61, "KJo": 0.60, "KTo": 0.59, "K9o": 0.56,
            "K8o": 0.54, "K7o": 0.53, "K6o": 0.52, "K5o": 0.51,
            "K4o": 0.50, "K3o": 0.49, "K2o": 0.48,
            "QJs": 0.62, "QTs": 0.61, "Q9s": 0.59, "Q8s": 0.57,
            "Q7s": 0.56, "Q6s": 0.54, "Q5s": 0.53, "Q4s": 0.52,
            "Q3s": 0.51, "Q2s": 0.50,
            "QJo": 0.58, "QTo": 0.57, "Q9o": 0.55, "Q8o": 0.53,
            "Q7o": 0.51, "Q6o": 0.50, "Q5o": 0.49, "Q4o": 0.48,
            "Q3o": 0.47, "Q2o": 0.46,
            "JTs": 0.60, "J9s": 0.58, "J8s": 0.56, "J7s": 0.54,
            "J6s": 0.53, "J5s": 0.51, "J4s": 0.50, "J3s": 0.49, "J2s": 0.48,
            "JTo": 0.56, "J9o": 0.54, "J8o": 0.52, "J7o": 0.50,
            "J6o": 0.49, "J5o": 0.47, "J4o": 0.46, "J3o": 0.45, "J2o": 0.44,
            "T9s": 0.57, "T8s": 0.55, "T7s": 0.53, "T6s": 0.51,
            "T5s": 0.50, "T4s": 0.49, "T3s": 0.48, "T2s": 0.47,
            "T9o": 0.53, "T8o": 0.51, "T7o": 0.49, "T6o": 0.47,
            "T5o": 0.46, "T4o": 0.45, "T3o": 0.44, "T2o": 0.43,
            "98s": 0.54, "97s": 0.52, "96s": 0.50, "95s": 0.49,
            "94s": 0.48, "93s": 0.47, "92s": 0.46,
            "98o": 0.50, "97o": 0.48, "96o": 0.46, "95o": 0.45,
            "94o": 0.44, "93o": 0.43, "92o": 0.42,
            "87s": 0.51, "86s": 0.49, "85s": 0.48, "84s": 0.47,
            "83s": 0.46, "82s": 0.45,
            "87o": 0.47, "86o": 0.45, "85o": 0.44, "84o": 0.43,
            "83o": 0.42, "82o": 0.41,
            "76s": 0.49, "75s": 0.48, "74s": 0.47, "73s": 0.46, "72s": 0.45,
            "76o": 0.45, "75o": 0.44, "74o": 0.43, "73o": 0.42, "72o": 0.41,
            "65s": 0.48, "64s": 0.47, "63s": 0.46, "62s": 0.45,
            "65o": 0.44, "64o": 0.43, "63o": 0.42, "62o": 0.41,
            "54s": 0.47, "53s": 0.46, "52s": 0.45,
            "54o": 0.43, "53o": 0.42, "52o": 0.41,
            "43s": 0.46, "42s": 0.45, "43o": 0.42, "42o": 0.41,
            "32s": 0.45, "32o": 0.41,
        }

        self.river_win_rates: dict[str, float] = {
            "straight flush": 0.99,
            "four of a kind": 0.97,
            "full house": 0.90,
            "flush": 0.82,
            "straight": 0.75,
            "three of a kind": 0.65,
            "two pair": 0.55,
            "pair": 0.32,
            "high card": 0.10,
        }

        self.hands_played = 0
        self.opp_folds = 0
        self.opp_raises = 0
        self.heavy_bets_faced = 0
        self.net_chips = 0
        self.stack_losses = 0

        self.street_folds: dict[str, int] = {}
        self.street_raises: dict[str, int] = {}

        self.mode = "BALANCED"

        self.equity_cache: dict = {}
        self._opp_bets_this_hand = 0

    def on_hand_start(self, game_info: GameInfo, current_state: PokerState) -> None:
        self.equity_cache = {}
        self._opp_bets_this_hand = 0
        self._update_mode()

    def on_hand_end(self, game_info: GameInfo, current_state: PokerState) -> None:
        self.hands_played += 1
        self.net_chips += current_state.payoff

        if current_state.payoff > 0 and len(current_state.opp_revealed_cards) < 2:
            self.opp_folds += 1
            street = current_state.street
            self.street_folds[street] = self.street_folds.get(street, 0) + 1

        if current_state.payoff < -1200:
            self.stack_losses += 1

    def _update_mode(self) -> None:
        if self.hands_played < 15:
            self.mode = "BALANCED"
            return

        fold_rate = self.opp_folds / max(1, self.hands_played)
        aggr_rate = self.heavy_bets_faced / max(1, self.hands_played)

        if self.net_chips < -2000 or self.stack_losses >= 3:
            self.mode = "CAUTIOUS"
        elif fold_rate > 0.50:
            self.mode = "EXPLOIT_PASSIVE"
        elif aggr_rate > 0.45:
            self.mode = "EXPLOIT_AGGRO"
        else:
            self.mode = "BALANCED"

    def _hand_key(self, cards: list[str]) -> str:
        """Convert two hole cards to a canonical 169-hand key."""
        rank_vals = {
            "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7,
            "8": 8, "9": 9, "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14,
        }
        r1, r2 = cards[0][0], cards[1][0]
        s1, s2 = cards[0][1], cards[1][1]
        v1, v2 = rank_vals[r1], rank_vals[r2]

        if v1 == v2:
            return f"{r1}{r2}"
        high, low = (r1, r2) if v1 > v2 else (r2, r1)
        suited = "s" if s1 == s2 else "o"
        return f"{high}{low}{suited}"

    def _preflop_eq(self, hand: list[str]) -> float:
        """O(1) preflop equity lookup."""
        return self.preflop_equity.get(self._hand_key(hand), 0.40)

    def _flop_abstract_key(self, hand: list[str], board: list[str]) -> str:
        """Build abstract state key for O(1) flop lookup."""
        my_cards = [eval7.Card(c) for c in hand]
        board_cards = [eval7.Card(c) for c in board]
        suits = [c.suit for c in board_cards]
        max_suit = max((suits.count(s) for s in set(suits)), default=0)

        if max_suit == 3:
            suit_str = "Monotone"
        elif max_suit == 2:
            suit_str = "TwoTone"
        else:
            suit_str = "Rainbow"

        ranks = sorted([c.rank for c in board_cards])
        paired = (
            "Paired"
            if len(ranks) >= 2 and len(set(ranks)) < len(ranks)
            else "Unpaired"
        )

        our_val = eval7.evaluate(my_cards + board_cards)
        raw_type = eval7.handtype(our_val)
        type_map = {
            "High Card": "HighCard",
            "Pair": "OnePair",
            "Two Pair": "TwoPair",
            "Trips": "ThreeOfAKind",
            "Three of a Kind": "ThreeOfAKind",
            "Straight": "Straight",
            "Flush": "Flush",
            "Full House": "FullHouse",
            "Four of a Kind": "FourOfAKind",
            "Quads": "FourOfAKind",
            "Straight Flush": "StraightFlush",
        }
        h_key = type_map.get(raw_type, raw_type.replace(" ", ""))
        return f"{h_key}_{suit_str}_{paired}"

    def _mc_equity(
        self,
        hand: list[str],
        board: list[str],
        opp_revealed: list[str],
        iters: int,
    ) -> float:
        """Monte Carlo equity calculation with caching."""
        cache_key = (tuple(hand), tuple(board), tuple(opp_revealed))
        if cache_key in self.equity_cache:
            return self.equity_cache[cache_key]

        deck = eval7.Deck()
        hole = [eval7.Card(c) for c in hand]
        board_c = [eval7.Card(c) for c in board]
        revealed = [eval7.Card(c) for c in opp_revealed]

        for card in hole + board_c + revealed:
            try:
                deck.cards.remove(card)
            except ValueError:
                pass

        score = 0
        for _ in range(iters):
            deck.shuffle()
            draw_count = 5 - len(board_c)
            draw = deck.peek(draw_count)

            if len(revealed) == 1:
                opp_hole = revealed + [deck.cards[draw_count]]
            elif len(revealed) == 2:
                opp_hole = revealed
            else:
                opp_hole = deck.cards[draw_count : draw_count + 2]

            our_val = eval7.evaluate(hole + board_c + draw)
            opp_val = eval7.evaluate(opp_hole + board_c + draw)

            if our_val > opp_val:
                score += 2
            elif our_val == opp_val:
                score += 1

        equity = score / (2 * iters)
        self.equity_cache[cache_key] = equity
        return equity

    def _get_equity(
        self,
        game_info: GameInfo,
        state: PokerState,
    ) -> float:
        """Get equity using the best available method for each street."""
        hand = state.my_hand
        board = state.board
        opp_revealed = state.opp_revealed_cards or []

        if state.street == "pre-flop":
            return self._preflop_eq(hand)

        if opp_revealed:
            iters = self._pick_iters(game_info, state.street)
            return self._mc_equity(hand, board, opp_revealed, iters)

        if state.street in ("flop", "auction"):
            key = self._flop_abstract_key(hand, board)
            if key in self.flop_equities:
                return self.flop_equities[key]
            iters = self._pick_iters(game_info, "flop")
            return self._mc_equity(hand, board, opp_revealed, iters)

        iters = self._pick_iters(game_info, state.street)
        return self._mc_equity(hand, board, opp_revealed, iters)

    def _pick_iters(self, game_info: GameInfo, street: str) -> int:
        """Choose MC iterations based on time budget and street."""
        if game_info.time_bank < 3.0:
            return 10
        if game_info.time_bank < 6.0:
            return 30
        if street == "flop":
            return 150
        if street == "turn":
            return 120
        return 60

    def _board_info(self, state: PokerState) -> dict:
        """Analyse the board and return a dict of texture features."""
        board = state.board
        hand = state.my_hand
        if not board:
            return {}

        my_cards = [eval7.Card(c) for c in hand]
        board_cards = [eval7.Card(c) for c in board]
        our_val = eval7.evaluate(my_cards + board_cards)
        h_type = eval7.handtype(our_val).lower()

        board_ranks = sorted([c.rank for c in board_cards])
        board_suits = [c.suit for c in board_cards]
        my_ranks = sorted([c.rank for c in my_cards], reverse=True)

        max_suit = max((board_suits.count(s) for s in set(board_suits)), default=0)
        is_flush_board = max_suit >= 3
        is_paired = len(set(board_ranks)) < len(board_ranks)

        is_connected = False
        if len(board_ranks) >= 3:
            for i in range(len(board_ranks) - 2):
                if board_ranks[i + 2] - board_ranks[i] <= 4:
                    is_connected = True
                    break

        max_board_rank = max(board_ranks) if board_ranks else 0

        danger = 0
        if is_paired:
            danger += 1
        if is_connected:
            danger += 1
        if is_flush_board:
            danger += 1

        return {
            "h_type": h_type,
            "our_val": our_val,
            "board_ranks": board_ranks,
            "board_suits": board_suits,
            "my_ranks": my_ranks,
            "max_board_rank": max_board_rank,
            "max_suit": max_suit,
            "is_flush_board": is_flush_board,
            "is_paired": is_paired,
            "is_connected": is_connected,
            "danger": danger,
        }

    def _adjust_equity(self, raw_eq: float, info: dict, cost: int, pot: int) -> float:
        """Adjust raw equity based on board texture.
        
        Uses ADDITIVE adjustments only — MC equity already accounts for hand
        strength, so multiplicative factors would double-count.
        """
        if not info:
            return raw_eq

        h = info["h_type"]
        is_flush_board = info["is_flush_board"]
        is_paired = info["is_paired"]

        eq = raw_eq

        if is_flush_board and h not in ("flush", "full house", "four of a kind", "straight flush"):
            eq -= 0.12

        if is_paired and h in ("high card", "pair"):
            eq -= 0.15
        elif is_paired and h == "two pair":
            eq -= 0.10
        elif is_paired and h in ("straight", "flush"):
            eq -= 0.08

        if cost > 0:
            prev_pot = max(1, pot - cost)
            bet_ratio = cost / prev_pot
            if bet_ratio > 1.2:
                eq -= 0.08
            elif bet_ratio > 0.75:
                eq -= 0.04

        return max(eq, 0.0)

    def _auction_bid(self, eq: float, state: PokerState) -> ActionBid:
        """
        Auction bidding: compete for information advantage.
        Information is most valuable with strong hands (confirm dominance)
        and medium hands (decide whether to continue).
        """
        pot = state.pot
        chips = state.my_chips

        if eq >= 0.75:
            bid = int(pot * random.uniform(1.2, 2.0))
        elif eq >= 0.55:
            bid = int(pot * random.uniform(0.50, 1.1))
        elif eq >= 0.40:
            if random.random() < 0.12:
                bid = 0
            else:
                bid = int(pot * random.uniform(0.20, 0.55))
        else:
            if random.random() < 0.70:
                bid = int(pot * random.uniform(0.0, 0.12))
            else:
                bid = int(pot * random.uniform(0.25, 0.50))

        bid = max(0, min(bid, chips))
        return ActionBid(bid)

    def _preflop_action(self, eq: float, state: PokerState) -> ActionFold | ActionCall | ActionCheck | ActionRaise:
        cost = state.cost_to_call
        pot = state.pot
        can_raise = state.can_act(ActionRaise)
        can_check = state.can_act(ActionCheck)
        is_sb = not state.is_bb

        if cost > 1000 and eq < 0.80:
            return ActionFold()
        if cost > 500 and eq < 0.72:
            return ActionFold()
        if cost > 200 and eq < 0.65:
            return ActionFold()
        if cost > 80 and eq < 0.55:
            return ActionFold()

        if eq >= 0.72 and can_raise:
            min_r, max_r = state.raise_bounds
            size = int(pot * 3.5)
            return ActionRaise(max(min_r, min(size, max_r)))

        if eq >= 0.62 and can_raise:
            min_r, max_r = state.raise_bounds
            size = int(pot * 2.8)
            return ActionRaise(max(min_r, min(size, max_r)))

        if eq >= 0.50 and can_raise:
            min_r, max_r = state.raise_bounds
            size = int(pot * 2.2)
            return ActionRaise(max(min_r, min(size, max_r)))

        if eq >= 0.45 and can_raise:
            min_r, max_r = state.raise_bounds
            size = int(pot * 2.0)
            return ActionRaise(max(min_r, min(size, max_r)))

        if cost > 20 and eq < 0.50:
            return ActionFold()

        if cost > 40 and eq < 0.55:
            return ActionFold()

        if eq >= 0.50:
            return ActionCall() if state.can_act(ActionCall) else ActionCheck()

        if can_check:
            return ActionCheck()

        if cost <= 20 and eq >= 0.45:
            return ActionCall() if state.can_act(ActionCall) else ActionFold()

        return ActionFold()

    def _postflop_action(
        self,
        eq: float,
        adj_eq: float,
        state: PokerState,
        info: dict,
    ) -> ActionFold | ActionCall | ActionCheck | ActionRaise:
        """GTO-inspired postflop play with balanced value/bluff ratios."""
        cost = state.cost_to_call
        pot = state.pot
        stack = state.my_chips
        can_raise = state.can_act(ActionRaise)
        can_check = state.can_act(ActionCheck)
        is_river = state.street == "river"
        h_type = info.get("h_type", "high card")
        danger = info.get("danger", 0)
        spr = stack / max(pot, 1)

        pot_odds = cost / (pot + cost) if (pot + cost) > 0 else 0

        is_paired_board = info.get("is_paired", False)

        if cost > 0:
            if is_paired_board and h_type in ("high card", "pair") and cost > pot * 0.4:
                return ActionFold()
            if is_paired_board and h_type == "two pair" and cost > pot * 0.7:
                return ActionFold()
            if cost > 800 and h_type in ("high card", "pair"):
                return ActionFold()
            if cost > pot * 2 and h_type == "high card":
                return ActionFold()
            if cost > stack * 0.6 and h_type in ("high card", "pair", "two pair"):
                if adj_eq < 0.85:
                    return ActionFold()
            if self._opp_bets_this_hand >= 2 and h_type in ("high card", "pair"):
                return ActionFold()
            if self._opp_bets_this_hand >= 2 and h_type == "two pair" and cost > pot * 0.5:
                return ActionFold()

        if cost > 0:
            return self._facing_bet(adj_eq, eq, cost, pot, stack, can_raise, is_river, h_type, danger, spr, pot_odds, state)

        return self._checked_to_us(adj_eq, pot, can_raise, is_river, h_type, danger, spr, state)

    def _facing_bet(
        self,
        adj_eq: float,
        raw_eq: float,
        cost: int,
        pot: int,
        stack: int,
        can_raise: bool,
        is_river: bool,
        h_type: str,
        danger: int,
        spr: float,
        pot_odds: float,
        state: PokerState,
    ):
        """Decision logic when facing an opponent bet."""

        if is_river:
            return self._river_facing_bet(adj_eq, cost, pot, h_type, danger, pot_odds, can_raise, state)

        if h_type in ("flush", "full house", "four of a kind", "straight flush"):
            call_thresh = max(pot_odds, 0.40)
        elif h_type in ("straight", "three of a kind"):
            call_thresh = max(pot_odds + 0.03, 0.45)
        elif h_type == "two pair":
            call_thresh = max(pot_odds + 0.05, 0.48)
        else:
            implied_boost = 0.05 if spr > 3 else 0.02
            call_thresh = pot_odds + 0.08 + implied_boost

        if self._opp_bets_this_hand >= 2:
            call_thresh += 0.08

        if adj_eq >= call_thresh:
            if adj_eq >= 0.82 and can_raise and cost < pot * 0.8 and spr > 2:
                min_r, max_r = state.raise_bounds
                size = int(pot * BET_LARGE)
                return ActionRaise(max(min_r, min(size, max_r)))
            return ActionCall()

        return ActionFold()

    def _river_facing_bet(
        self,
        adj_eq: float,
        cost: int,
        pot: int,
        h_type: str,
        danger: int,
        pot_odds: float,
        can_raise: bool,
        state: PokerState,
    ):
        """River-specific calling/folding logic using empirical win rates."""
        empirical = self.river_win_rates.get(h_type, 0.10)

        if danger >= 2:
            empirical *= 0.75
        elif danger >= 1:
            empirical *= 0.85

        bet_ratio = cost / max(pot - cost, 1)
        if bet_ratio > 1.0:
            empirical *= 0.80
        elif bet_ratio > 0.75:
            empirical *= 0.90

        if empirical < 0.15:
            return ActionFold()

        if pot_odds >= empirical:
            return ActionFold()

        if adj_eq >= 0.90 and can_raise and h_type in ("full house", "four of a kind", "straight flush", "flush"):
            min_r, max_r = state.raise_bounds
            size = int(pot * BET_LARGE)
            return ActionRaise(max(min_r, min(size, max_r)))

        return ActionCall()

    def _checked_to_us(
        self,
        adj_eq: float,
        pot: int,
        can_raise: bool,
        is_river: bool,
        h_type: str,
        danger: int,
        spr: float,
        state: PokerState,
    ):
        """Decision logic when checked to us (we're in position or opponent checked)."""
        can_check = state.can_act(ActionCheck)

        if not can_raise:
            return ActionCheck() if can_check else ActionCall()

        min_r, max_r = state.raise_bounds

        if adj_eq >= 0.88:
            if not is_river and random.random() < 0.20:
                return ActionCheck()
            size = int(pot * BET_MEDIUM)
            return ActionRaise(max(min_r, min(size, max_r)))

        if adj_eq >= 0.70:
            if is_river:
                size = int(pot * BET_SMALL)
            else:
                size = int(pot * BET_MEDIUM)
            return ActionRaise(max(min_r, min(size, max_r)))

        if adj_eq >= 0.55:
            if danger <= 1 and not is_river:
                size = int(pot * BET_SMALL)
                return ActionRaise(max(min_r, min(size, max_r)))
            return ActionCheck()

        if not is_river and pot < 400:
            bluff_freq = self._bluff_frequency(state)
            if random.random() < bluff_freq:
                size = int(pot * BET_SMALL)
                return ActionRaise(max(min_r, min(size, max_r)))

        if is_river and adj_eq < 0.20 and pot < 500:
            bluff_freq = self._bluff_frequency(state) * 0.6
            if random.random() < bluff_freq:
                size = int(pot * BET_MEDIUM)
                return ActionRaise(max(min_r, min(size, max_r)))

        return ActionCheck()

    def _bluff_frequency(self, state: PokerState) -> float:
        """Calculate bluff frequency based on opponent tendencies and mode."""
        if self.hands_played < 10:
            return 0.12

        fold_rate = self.opp_folds / max(1, self.hands_played)
        street_fold = self.street_folds.get(state.street, 0) / max(1, self.hands_played)

        if self.mode == "EXPLOIT_PASSIVE":
            return min(0.35, fold_rate * 0.6 + 0.05)
        elif self.mode == "EXPLOIT_AGGRO":
            return 0.05
        elif self.mode == "CAUTIOUS":
            return 0.04
        else:
            return min(0.25, 0.12 + street_fold * 0.5)

    def get_move(
        self, game_info: GameInfo, current_state: PokerState
    ) -> ActionFold | ActionCall | ActionCheck | ActionRaise | ActionBid:
        cost = current_state.cost_to_call
        pot = current_state.pot

        if cost > pot * 0.5 or cost > 150:
            self.heavy_bets_faced += 1
        if cost > 0:
            self.opp_raises += 1
            if current_state.street not in ("pre-flop", "auction"):
                self._opp_bets_this_hand += 1

        raw_eq = self._get_equity(game_info, current_state)

        if current_state.street == "auction":
            return self._auction_bid(raw_eq, current_state)

        if current_state.street == "pre-flop":
            return self._preflop_action(raw_eq, current_state)

        info = self._board_info(current_state)
        adj_eq = self._adjust_equity(raw_eq, info, cost, pot)

        return self._postflop_action(raw_eq, adj_eq, current_state, info)


if __name__ == "__main__":
    run_bot(Player(), parse_args())
