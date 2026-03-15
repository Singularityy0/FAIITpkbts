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
import itertools
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
RAISE_HANDS = {"three of a kind", "straight", "flush", "full house", "four of a kind", "straight flush"}

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
        self._opp_has_info = False
        self._auction_resolved = False
        self._opp_bet_sizes: list[float] = []
        self._my_bets_this_hand = 0
        self._eq_from_mc = False

    def on_hand_start(self, game_info: GameInfo, current_state: PokerState) -> None:
        self.equity_cache = {}
        self._opp_bets_this_hand = 0
        self._opp_has_info = False
        self._auction_resolved = False
        self._opp_bet_sizes = []
        self._my_bets_this_hand = 0
        self._eq_from_mc = False
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

        if aggr_rate > 0.40:
            self.mode = "EXPLOIT_AGGRO"
        elif self.net_chips < -2000 or self.stack_losses >= 3:
            self.mode = "CAUTIOUS"
        elif fold_rate > 0.50:
            self.mode = "EXPLOIT_PASSIVE"
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

    def _exact_river_equity(
        self,
        hand: list[str],
        board: list[str],
        opp_revealed: list[str],
    ) -> float:
        """Exact combinatorial river equity — zero statistical noise.

        On the river all 5 community cards are known, so we enumerate every
        possible opponent holding (C(45,2)=990 at most) and compute the true
        win/tie/loss ratio.  Sub-millisecond even for the worst case.
        """
        cache_key = (tuple(hand), tuple(board), tuple(opp_revealed))
        if cache_key in self.equity_cache:
            return self.equity_cache[cache_key]

        hole = [eval7.Card(c) for c in hand]
        board_c = [eval7.Card(c) for c in board]
        revealed = [eval7.Card(c) for c in opp_revealed]

        deck = eval7.Deck()
        for card in hole + board_c + revealed:
            try:
                deck.cards.remove(card)
            except ValueError:
                pass
        remaining = deck.cards

        our_val = eval7.evaluate(hole + board_c)
        opp_need = 2 - len(revealed)
        score = 0
        total = 0

        if opp_need == 0:
            opp_val = eval7.evaluate(revealed + board_c)
            total = 1
            score = 2 if our_val > opp_val else (1 if our_val == opp_val else 0)
        elif opp_need == 1:
            for card in remaining:
                opp_hole = revealed + [card]
                opp_val = eval7.evaluate(opp_hole + board_c)
                if our_val > opp_val:
                    score += 2
                elif our_val == opp_val:
                    score += 1
                total += 1
        else:
            for c1, c2 in itertools.combinations(remaining, 2):
                opp_val = eval7.evaluate([c1, c2] + board_c)
                if our_val > opp_val:
                    score += 2
                elif our_val == opp_val:
                    score += 1
                total += 1

        equity = score / (2 * total) if total else 0.5
        self.equity_cache[cache_key] = equity
        return equity

    def _mc_equity(
        self,
        hand: list[str],
        board: list[str],
        opp_revealed: list[str],
        iters: int,
    ) -> float:
        """Monte Carlo equity for flop/turn (where exact is intractable)."""
        cache_key = (tuple(hand), tuple(board), tuple(opp_revealed))
        if cache_key in self.equity_cache:
            return self.equity_cache[cache_key]

        hole = [eval7.Card(c) for c in hand]
        board_c = [eval7.Card(c) for c in board]
        revealed = [eval7.Card(c) for c in opp_revealed]

        deck = eval7.Deck()
        for card in hole + board_c + revealed:
            try:
                deck.cards.remove(card)
            except ValueError:
                pass
        remaining = deck.cards

        draw_count = 5 - len(board_c)
        opp_need = 2 - len(revealed)
        total_need = draw_count + opp_need

        score = 0
        for _ in range(iters):
            sample = random.sample(remaining, total_need)
            draw = sample[:draw_count]
            full_board = board_c + draw
            opp_hole = list(revealed) + sample[draw_count:]
            our_val = eval7.evaluate(hole + full_board)
            opp_val = eval7.evaluate(opp_hole + full_board)
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
        """Get equity: preflop lookup, auction lookup, postflop MC."""
        hand = state.my_hand
        board = state.board
        opp_revealed = state.opp_revealed_cards or []

        if state.street == "pre-flop":
            self._eq_from_mc = False
            return self._preflop_eq(hand)

        # Auction: use fast lookup (bidding is less accuracy-critical)
        if state.street == "auction":
            key = self._flop_abstract_key(hand, board)
            if key in self.flop_equities:
                self._eq_from_mc = False
                return self.flop_equities[key]
            self._eq_from_mc = True
            return self._mc_equity(hand, board, opp_revealed, 100)

        # River: exact combinatorial equity (zero noise, sub-ms)
        if state.street == "river":
            self._eq_from_mc = True
            return self._exact_river_equity(hand, board, opp_revealed)

        # Flop/Turn: MC simulation
        self._eq_from_mc = True
        iters = self._pick_iters(game_info, state.street)
        return self._mc_equity(hand, board, opp_revealed, iters)

    def _pick_iters(self, game_info: GameInfo, street: str) -> int:
        """Choose MC iterations based on time budget."""
        if game_info.time_bank < 3.0:
            return 50
        if game_info.time_bank < 6.0:
            return 150
        return 1000

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
        """Adjust equity for board texture (lookup only) and opponent behavior (always).
        
        Board texture adjustments are skipped when using MC equity because the
        simulation already accounts for flush/paired board effects.  Behavioral
        adjustments always apply since MC assumes a random opponent hand.
        """
        if not info:
            return raw_eq

        h = info["h_type"]
        eq = raw_eq

        # Board texture, only when using lookup table 
        if not self._eq_from_mc:
            is_flush_board = info["is_flush_board"]
            is_paired = info["is_paired"]

            if is_flush_board and h not in ("flush", "full house", "four of a kind", "straight flush"):
                eq -= 0.12

            if is_paired and h in ("high card", "pair"):
                eq -= 0.15
            elif is_paired and h == "two pair":
                eq -= 0.10
            elif is_paired and h in ("straight", "flush"):
                eq -= 0.08

        # Behavioral adjustments — skip when exploiting aggro (their big bets don't mean strength)
        if cost > 0 and self.mode != "EXPLOIT_AGGRO":
            prev_pot = max(1, pot - cost)
            bet_ratio = cost / prev_pot
            if bet_ratio > 1.2:
                eq -= 0.08
            elif bet_ratio > 0.75:
                eq -= 0.04

        if self._opp_has_info:
            if h in ("high card", "pair"):
                eq -= 0.14
            elif h == "two pair":
                eq -= 0.08
            elif h == "three of a kind":
                eq -= 0.04
            else:
                eq -= 0.03

        if cost > 0 and self._opp_bet_sizes and self.mode != "EXPLOIT_AGGRO":
            n = len(self._opp_bet_sizes)
            avg = sum(self._opp_bet_sizes) / n
            eq -= min(0.15, n * 0.03 * (1 + avg * 0.4))

        return max(eq, 0.0)

    def _auction_bid(self, eq: float, state: PokerState) -> ActionBid:
        """
        Auction bidding: winner pays LOSER's bid.
        Our bid = price opponent pays if they outbid us to see our card.
        Bid high with strong hands to protect info AND get cheap info.
        Never bid 0 (that gives opponent free information).
        Cap bids to prevent catastrophic auction overspend in bloated pots.
        """
        pot = state.pot
        chips = state.my_chips

        if eq >= 0.75:
            bid = int(pot * random.uniform(0.85, 1.40))
        elif eq >= 0.55:
            bid = int(pot * random.uniform(0.55, 0.90))
        elif eq >= 0.40:
            bid = int(pot * random.uniform(0.40, 0.65))
        else:
            bid = int(pot * random.uniform(0.30, 0.50))

        # cap the auction cause i dont want to bleed much chips here, it's just for info
        bid = min(bid, max(200, int(chips * 0.08)))
        bid = max(1, min(bid, chips))
        return ActionBid(bid)

    def _preflop_action(self, eq: float, state: PokerState) -> ActionFold | ActionCall | ActionCheck | ActionRaise:
        cost = state.cost_to_call
        pot = state.pot
        can_raise = state.can_act(ActionRaise)
        can_check = state.can_act(ActionCheck)
        facing_raise = cost > BIG_BLIND  

        # thresholds — loosen when exploiting aggro (their raises are wide)
        aggro = self.mode == "EXPLOIT_AGGRO"
        if cost > 1000 and eq < (0.72 if aggro else 0.80):
            return ActionFold()
        if cost > 500 and eq < (0.65 if aggro else 0.72):
            return ActionFold()
        if cost > 200 and eq < (0.55 if aggro else 0.65):
            return ActionFold()
        if cost > 80 and eq < (0.45 if aggro else 0.58):
            return ActionFold()

        # if opponent raises , i will need a stronger hand to continue, and i will be more inclined to fold weaker hands
        if facing_raise and can_raise:
            reraise_thresh = 0.72 if aggro else 0.80
            call_thresh_pf = 0.50 if aggro else 0.55
            if eq >= reraise_thresh:
                min_r, max_r = state.raise_bounds
                size = int(pot * 3.0)
                return ActionRaise(max(min_r, min(size, max_r)))
            elif eq >= call_thresh_pf:
                return ActionCall() if state.can_act(ActionCall) else ActionCheck()
            elif cost > 40:
                return ActionFold()
            else:
                return ActionCall() if state.can_act(ActionCall) else ActionFold()

        # not facing a raise, so i can be more flexible with our hand selection and bet sizing
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

        # Call with playable hands
        if eq >= 0.50:
            return ActionCall() if state.can_act(ActionCall) else ActionCheck()

        if can_check:
            return ActionCheck()

        # Limp only when cheap with borderline hands
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

        # Pot commitment: estimate our investment so far
        our_investment = (pot - cost) // 2  # rough share of pot we've built
        committed = our_investment > STARTING_STACK * 0.25

        if cost > 0:
            if is_paired_board and h_type in ("high card", "pair") and cost > pot * 0.3:
                return ActionFold()
            if is_paired_board and h_type == "two pair" and cost > pot * 0.40:
                return ActionFold()
            if cost > 800 and h_type in ("high card", "pair") and not committed:
                if not (self.mode == "EXPLOIT_AGGRO" and h_type == "pair"):
                    return ActionFold()
            if cost > pot * 2 and h_type == "high card":
                return ActionFold()
            shove_req = 0.65 if self.mode == "EXPLOIT_AGGRO" else 0.85
            if cost > stack * 0.6 and h_type in ("high card", "pair", "two pair"):
                if adj_eq < shove_req:
                    return ActionFold()
            if self._opp_bets_this_hand >= 2 and h_type == "high card" and not committed:
                return ActionFold()
            if self._opp_bets_this_hand >= 2 and h_type == "pair" and not committed and cost > pot * 0.25:
                if self.mode != "EXPLOIT_AGGRO":
                    return ActionFold()
            if self._opp_bets_this_hand >= 2 and h_type == "two pair" and cost > pot * 0.5 and not committed:
                if self.mode != "EXPLOIT_AGGRO":
                    return ActionFold()

            # Asymmetric info: fold high card to significant bets when opponent has info
            if self._opp_has_info and h_type == "high card" and cost > pot * 0.3:
                return ActionFold()

        if cost > 0:
            return self._facing_bet(adj_eq, eq, cost, pot, stack, can_raise, is_river, h_type, danger, spr, pot_odds, state)

        return self._checked_to_us(adj_eq, pot, can_raise, is_river, h_type, danger, spr, state, info)

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

        # Maniac fix: drastically lower required equity vs aggro players
        if self.mode == "EXPLOIT_AGGRO":
            if h_type in ("high card", "pair"):
                call_thresh -= 0.15
            else:
                call_thresh -= 0.05

        if self._my_bets_this_hand >= 1 and h_type not in ("high card",):
            call_thresh = min(call_thresh, pot_odds + 0.05)

        if self._should_act(adj_eq, call_thresh):
            if adj_eq >= 0.82 and can_raise and cost < pot * 0.8 and spr > 2:
                min_r, max_r = state.raise_bounds
                if h_type in RAISE_HANDS:
                    size = int(pot * BET_LARGE)
                else:
                    size = int(pot * BET_MEDIUM)  
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
        """River calling/folding using MC-adjusted equity (per-hand accurate)."""
        if adj_eq < 0.12:
            return ActionFold()

        # Fold weak hands: multi-barrel (3+ streets aggression) or large river bets
        if h_type in ("pair", "high card") and adj_eq < 0.55:
            if self._opp_bets_this_hand >= 2 or cost > pot * 0.4:
                return ActionFold()

        if not self._should_act(adj_eq, pot_odds, 0.04):
            return ActionFold()

        if adj_eq >= 0.88 and can_raise and h_type in RAISE_HANDS:
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
        info: dict | None = None,
    ):
        """Decision logic when checked to us (we're in position or opponent checked).
        only bet if we can continue when raised."""
        can_check = state.can_act(ActionCheck)

        if not can_raise:
            return ActionCheck() if can_check else ActionCall()

        # Underpair check-back: don't barrel past flop with pocket pair below board
        if h_type == "pair" and state.street != "flop" and info:
            my_r = info.get("my_ranks", [14])
            max_br = info.get("max_board_rank", 0)
            if len(my_r) >= 2 and my_r[0] == my_r[1] and my_r[0] < max_br:
                return ActionCheck()

        min_r, max_r = state.raise_bounds

        # Exploit passive opponents: lower value-bet threshold
        vbet_strong = 0.65 if self.mode == "EXPLOIT_PASSIVE" else 0.70

        # sizing scales with hand category
        if adj_eq >= 0.88:
            if not is_river and random.random() < 0.20:
                return ActionCheck()
            size = int(pot * BET_MEDIUM)
            return ActionRaise(max(min_r, min(size, max_r)))

        #  trips+ get normal sizing; pair/two pair controlled sizing
        if adj_eq >= vbet_strong:
            if is_river and h_type in ("pair", "high card"):
                return ActionCheck()
            if h_type in RAISE_HANDS:
                size = int(pot * BET_SMALL) if is_river else int(pot * BET_MEDIUM)
            else:
                size = int(pot * BET_SMALL) if is_river else int(pot * BET_MEDIUM)
            return ActionRaise(max(min_r, min(size, max_r)))

        # c-bet on safe boards with decent hands (flop only)
        if adj_eq >= 0.55 and not is_river:
            if danger <= 1:
                size = int(pot * BET_SMALL)
                return ActionRaise(max(min_r, min(size, max_r)))
            return ActionCheck()

        # Bluffs: only on flop, small pots
        if not is_river and state.street == "flop" and pot < 400:
            bluff_freq = self._bluff_frequency(state)
            if random.random() < bluff_freq:
                size = int(pot * BET_SMALL)
                return ActionRaise(max(min_r, min(size, max_r)))

        return ActionCheck()

    def _bluff_frequency(self, state: PokerState) -> float:
        """Calculate bluff frequency based on opponent tendencies and mode."""
        if self.hands_played < 10:
            freq = 0.10
        else:
            fold_rate = self.opp_folds / max(1, self.hands_played)
            street_fold = self.street_folds.get(state.street, 0) / max(1, self.hands_played)

            if self.mode == "EXPLOIT_PASSIVE":
                freq = min(0.30, fold_rate * 0.5 + 0.05)
            elif self.mode == "EXPLOIT_AGGRO":
                freq = 0.03
            elif self.mode == "CAUTIOUS":
                freq = 0.02
            else:
                freq = min(0.20, 0.10 + street_fold * 0.4)

        if self._opp_has_info:
            freq *= 0.20
        return freq

    def _should_act(self, eq: float, threshold: float, margin: float = 0.04) -> bool:
        """Mixed strategy: smooth probability transition around threshold.
        Returns True above threshold+margin, False below threshold-margin,
        and with linear probability in between."""
        if eq >= threshold + margin:
            return True
        if eq < threshold - margin:
            return False
        p = (eq - (threshold - margin)) / (2 * margin)
        return random.random() < p

    def get_move(
        self, game_info: GameInfo, current_state: PokerState
    ) -> ActionFold | ActionCall | ActionCheck | ActionRaise | ActionBid:
        cost = current_state.cost_to_call
        pot = current_state.pot

        if (current_state.street == "pre-flop" and cost > 100) or (current_state.street != "pre-flop" and cost > pot * 0.5) or cost > 200:
            self.heavy_bets_faced += 1
        if cost > 0:
            self.opp_raises += 1
            if current_state.street not in ("pre-flop", "auction"):
                self._opp_bets_this_hand += 1
                self._opp_bet_sizes.append(cost / max(pot - cost, 1))

        if current_state.street not in ("pre-flop", "auction") and not self._auction_resolved:
            self._auction_resolved = True
            if not current_state.opp_revealed_cards:
                self._opp_has_info = True

        raw_eq = self._get_equity(game_info, current_state)

        if current_state.street == "auction":
            return self._auction_bid(raw_eq, current_state)

        if current_state.street == "pre-flop":
            return self._preflop_action(raw_eq, current_state)

        info = self._board_info(current_state)
        adj_eq = self._adjust_equity(raw_eq, info, cost, pot)

        action = self._postflop_action(raw_eq, adj_eq, current_state, info)

        if info.get("is_paired", False) and info.get("h_type", "") not in (
            "full house", "four of a kind", "straight flush"
        ):
            if isinstance(action, ActionRaise) and action.amount > int(current_state.pot * 0.75):
                min_r, max_r = current_state.raise_bounds
                capped = max(min_r, min(int(current_state.pot * BET_MEDIUM), max_r))
                action = ActionRaise(capped)
            if isinstance(action, ActionCall) and current_state.cost_to_call > current_state.my_chips * 0.40:
                if adj_eq < 0.96:
                    action = ActionFold()

        if isinstance(action, ActionRaise):
            self._my_bets_this_hand += 1

        return action


if __name__ == "__main__":
    run_bot(Player(), parse_args())
