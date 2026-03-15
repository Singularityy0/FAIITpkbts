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
        self.preflop_equity = {
            "AA": 0.85,
            "KK": 0.82,
            "QQ": 0.80,
            "JJ": 0.77,
            "TT": 0.75,
            "99": 0.72,
            "88": 0.69,
            "77": 0.66,
            "66": 0.63,
            "55": 0.60,
            "44": 0.57,
            "33": 0.54,
            "22": 0.51,
            "AKs": 0.67,
            "AQs": 0.66,
            "AJs": 0.65,
            "ATs": 0.64,
            "A9s": 0.62,
            "A8s": 0.61,
            "A7s": 0.60,
            "A6s": 0.59,
            "A5s": 0.60,
            "A4s": 0.59,
            "A3s": 0.58,
            "A2s": 0.57,
            "AKo": 0.65,
            "AQo": 0.63,
            "AJo": 0.62,
            "ATo": 0.61,
            "A9o": 0.58,
            "A8o": 0.57,
            "A7o": 0.56,
            "A6o": 0.55,
            "A5o": 0.55,
            "A4o": 0.54,
            "A3o": 0.53,
            "A2o": 0.52,
            "KQs": 0.64,
            "KJs": 0.63,
            "KTs": 0.62,
            "K9s": 0.60,
            "K8s": 0.58,
            "K7s": 0.57,
            "K6s": 0.56,
            "K5s": 0.55,
            "K4s": 0.54,
            "K3s": 0.53,
            "K2s": 0.52,
            "KQo": 0.61,
            "KJo": 0.60,
            "KTo": 0.59,
            "K9o": 0.56,
            "K8o": 0.54,
            "K7o": 0.53,
            "K6o": 0.52,
            "K5o": 0.51,
            "K4o": 0.50,
            "K3o": 0.49,
            "K2o": 0.48,
            "QJs": 0.62,
            "QTs": 0.61,
            "Q9s": 0.59,
            "Q8s": 0.57,
            "Q7s": 0.56,
            "Q6s": 0.54,
            "Q5s": 0.53,
            "Q4s": 0.52,
            "Q3s": 0.51,
            "Q2s": 0.50,
            "QJo": 0.58,
            "QTo": 0.57,
            "Q9o": 0.55,
            "Q8o": 0.53,
            "Q7o": 0.51,
            "Q6o": 0.50,
            "Q5o": 0.49,
            "Q4o": 0.48,
            "Q3o": 0.47,
            "Q2o": 0.46,
            "JTs": 0.60,
            "J9s": 0.58,
            "J8s": 0.56,
            "J7s": 0.54,
            "J6s": 0.53,
            "J5s": 0.51,
            "J4s": 0.50,
            "J3s": 0.49,
            "J2s": 0.48,
            "JTo": 0.56,
            "J9o": 0.54,
            "J8o": 0.52,
            "J7o": 0.50,
            "J6o": 0.49,
            "J5o": 0.47,
            "J4o": 0.46,
            "J3o": 0.45,
            "J2o": 0.44,
            "T9s": 0.57,
            "T8s": 0.55,
            "T7s": 0.53,
            "T6s": 0.51,
            "T5s": 0.50,
            "T4s": 0.49,
            "T3s": 0.48,
            "T2s": 0.47,
            "T9o": 0.53,
            "T8o": 0.51,
            "T7o": 0.49,
            "T6o": 0.47,
            "T5o": 0.46,
            "T4o": 0.45,
            "T3o": 0.44,
            "T2o": 0.43,
            "98s": 0.54,
            "97s": 0.52,
            "96s": 0.50,
            "95s": 0.49,
            "94s": 0.48,
            "93s": 0.47,
            "92s": 0.46,
            "98o": 0.50,
            "97o": 0.48,
            "96o": 0.46,
            "95o": 0.45,
            "94o": 0.44,
            "93o": 0.43,
            "92o": 0.42,
            "87s": 0.51,
            "86s": 0.49,
            "85s": 0.48,
            "84s": 0.47,
            "83s": 0.46,
            "82s": 0.45,
            "87o": 0.47,
            "86o": 0.45,
            "85o": 0.44,
            "84o": 0.43,
            "83o": 0.42,
            "82o": 0.41,
            "76s": 0.49,
            "75s": 0.48,
            "74s": 0.47,
            "73s": 0.46,
            "72s": 0.45,
            "76o": 0.45,
            "75o": 0.44,
            "74o": 0.43,
            "73o": 0.42,
            "72o": 0.41,
            "65s": 0.48,
            "64s": 0.47,
            "63s": 0.46,
            "62s": 0.45,
            "65o": 0.44,
            "64o": 0.43,
            "63o": 0.42,
            "62o": 0.41,
            "54s": 0.47,
            "53s": 0.46,
            "52s": 0.45,
            "54o": 0.43,
            "53o": 0.42,
            "52o": 0.41,
            "43s": 0.46,
            "42s": 0.45,
            "43o": 0.42,
            "42o": 0.41,
            "32s": 0.45,
            "32o": 0.41,
        }

    def _hand_key(self, cards):
        r1, r2 = cards[0][0], cards[1][0]
        s1, s2 = cards[0][1], cards[1][1]
        vals = {
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
        v1, v2 = vals[r1], vals[r2]

        if v1 == v2:
            return f"{r1}{r2}"
        high, low = (r1, r2) if v1 > v2 else (r2, r1)
        suited = "s" if s1 == s2 else "o"
        return f"{high}{low}{suited}"

    def _preflop_eq(self, hand):
        key = self._hand_key(hand)
        return self.preflop_equity.get(key, 0.40)

    def _postflop_eq(self, hand, board, opp_revealed, iters=150):
        cache_key = (tuple(hand), tuple(board), tuple(opp_revealed))
        if cache_key in self.equity_cache:
            return self.equity_cache[cache_key]

        try:
            deck = eval7.Deck()
            my_cards = [eval7.Card(c) for c in hand]
            board_cards = [eval7.Card(c) for c in board]
            revealed_cards = [eval7.Card(c) for c in opp_revealed]

            for card in my_cards + board_cards + revealed_cards:
                deck.cards.remove(card)

            wins = 0
            for _ in range(iters):
                deck.shuffle()
                draw_count = 5 - len(board)
                draw = deck.peek(draw_count)

                if len(revealed_cards) == 1:
                    opp_hand = revealed_cards + [deck.cards[draw_count]]
                elif len(revealed_cards) == 2:
                    opp_hand = revealed_cards
                else:
                    opp_hand = deck.cards[draw_count : draw_count + 2]

                my_val = eval7.evaluate(my_cards + board_cards + draw)
                opp_val = eval7.evaluate(opp_hand + board_cards + draw)

                if my_val > opp_val:
                    wins += 2
                elif my_val == opp_val:
                    wins += 1

            equity = wins / (2 * iters)
            self.equity_cache[cache_key] = equity
            return equity
        except:
            return 0.50

    def on_hand_start(self, game_info: GameInfo, game_state: PokerState) -> None:
        self.equity_cache = {}
        self.hands_played += 1

    def on_hand_end(self, game_info: GameInfo, game_state: PokerState) -> None:
        pass

    def get_move(self, game_info: GameInfo, game_state: PokerState):
        legal = game_state.legal_actions
        hand = game_state.my_hand
        pot = game_state.pot
        cost = game_state.cost_to_call
        stack = game_state.my_chips
        board = game_state.board
        opp_revealed = (
            game_state.opp_revealed_cards if game_state.opp_revealed_cards else []
        )

        if ActionBid in legal:
            eq = (
                self._postflop_eq(hand, board, opp_revealed, 80)
                if board
                else self._preflop_eq(hand)
            )
            if eq > 0.65:
                return ActionBid(min(int(pot * 1.2), stack // 3))
            elif eq > 0.50:
                return ActionBid(min(int(pot * 0.4), stack // 5))
            else:
                return ActionBid(min(int(pot * 0.15), 50))

        if game_state.street == "pre-flop":
            eq = self._preflop_eq(hand)

            if cost > 1000:
                return ActionFold() if eq < 0.82 else ActionCall()
            if cost > 500:
                return ActionFold() if eq < 0.75 else ActionCall()
            if cost > 200:
                return ActionFold() if eq < 0.68 else ActionCall()
            if cost > 100:
                return ActionFold() if eq < 0.62 else ActionCall()

            if eq >= 0.65:
                if ActionRaise in legal:
                    min_r, max_r = game_state.raise_bounds
                    size = int(pot * 3.5) if eq >= 0.75 else int(pot * 2.8)
                    return ActionRaise(max(min_r, min(size, max_r)))
                return ActionCall() if ActionCall in legal else ActionCheck()

            elif eq >= 0.50:
                if ActionRaise in legal and cost == 0:
                    min_r, max_r = game_state.raise_bounds
                    return ActionRaise(max(min_r, min(int(pot * 2.2), max_r)))
                if cost <= pot * 0.4:
                    return ActionCall() if ActionCall in legal else ActionCheck()
                return ActionFold()

            elif eq >= 0.40:
                if ActionRaise in legal and cost == 0:
                    min_r, max_r = game_state.raise_bounds
                    return ActionRaise(max(min_r, min(int(pot * 1.8), max_r)))
                if cost <= 20:
                    return ActionCall() if ActionCall in legal else ActionCheck()
                return ActionFold()

            else:
                return (
                    ActionCheck()
                    if ActionCheck in legal
                    else (ActionCall() if cost <= 10 else ActionFold())
                )

        else:
            iters = 180 if game_state.street == "turn" else 150
            eq = self._postflop_eq(hand, board, opp_revealed, iters)

            my_cards = [eval7.Card(c) for c in hand]
            board_cards = [eval7.Card(c) for c in board]
            my_val = eval7.evaluate(my_cards + board_cards)
            hand_strength = eval7.handtype(my_val).lower()
            is_river = game_state.street == "river"

            board_ranks = [c[0] for c in board]
            paired_board = len(board_ranks) != len(set(board_ranks))
            connected_board = False
            if len(board_ranks) >= 3:
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
                sorted_vals = sorted([rank_vals[r] for r in board_ranks])
                for i in range(len(sorted_vals) - 2):
                    if sorted_vals[i + 2] - sorted_vals[i] <= 4:
                        connected_board = True
                        break

            danger_factor = 0
            if paired_board:
                danger_factor += 1
            if connected_board:
                danger_factor += 1
            suits = [c[1] for c in board]
            if suits and max([suits.count(s) for s in set(suits)]) >= 3:
                danger_factor += 1

            spr = stack / max(pot, 1)

            if cost > stack * 0.6:
                if is_river and hand_strength in [
                    "pair",
                    "two pair",
                    "high card",
                    "straight",
                    "three of a kind",
                    "flush",
                ]:
                    return ActionFold()
                return ActionCall() if eq >= 0.90 else ActionFold()

            if cost > 800:
                if hand_strength in ["high card", "pair"]:
                    return ActionFold()
                if hand_strength == "two pair" and danger_factor >= 2:
                    return ActionFold()
                if is_river and hand_strength in [
                    "two pair",
                    "straight",
                    "three of a kind",
                    "flush",
                ]:
                    return ActionFold()
                return ActionCall() if eq >= 0.85 else ActionFold()

            if cost > pot * 2:
                if hand_strength == "high card":
                    return ActionFold()
                if hand_strength == "pair" and danger_factor >= 1:
                    return ActionFold()
                return ActionCall() if eq >= 0.82 else ActionFold()

            if cost > pot:
                if hand_strength == "high card" and danger_factor >= 1:
                    return ActionFold()
                if hand_strength == "pair" and danger_factor >= 2:
                    return ActionFold()

            if cost > 0:
                pot_odds = cost / (pot + cost)
                implied_odds_boost = 0.05 if spr > 3 else 0.02
                call_threshold = pot_odds + 0.10 + implied_odds_boost
                if is_river:
                    RIVER_WIN_RATES = {
                        "straight flush": 0.95,
                        "four of a kind": 0.67,
                        "full house": 0.56,
                        "flush": 0.29,
                        "straight": 0.31,
                        "three of a kind": 0.35,
                        "two pair": 0.24,
                        "pair": 0.0,
                        "high card": 0.0,
                    }
                    empirical_win = RIVER_WIN_RATES.get(hand_strength, 0.0)

                    if empirical_win == 0.0:
                        return ActionFold()

                    if paired_board and hand_strength in [
                        "flush",
                        "straight",
                        "three of a kind",
                        "two pair",
                    ]:
                        empirical_win *= 0.75
                    board_suits = [c[1] for c in board]
                    if (
                        board_suits
                        and max(board_suits.count(s) for s in set(board_suits)) >= 3
                    ):
                        if hand_strength in ["straight", "three of a kind", "two pair"]:
                            empirical_win *= 0.80

                    bet_ratio = cost / max(pot, 1)
                    if bet_ratio > 1.0:
                        empirical_win *= 0.75
                    elif bet_ratio > 0.75:
                        empirical_win *= 0.85

                    if pot_odds >= empirical_win:
                        return ActionFold()

                    call_threshold = max(pot_odds + 0.05, empirical_win - 0.05)

                if not is_river and hand_strength in [
                    "flush",
                    "full house",
                    "four of a kind",
                    "straight flush",
                ]:
                    call_threshold = max(pot_odds, 0.50)
                elif hand_strength in ["straight", "three of a kind"] and not is_river:
                    call_threshold = max(pot_odds + 0.05, 0.55)

                if eq >= call_threshold:
                    if (
                        eq >= 0.88
                        and ActionRaise in legal
                        and cost < pot * 0.6
                        and spr > 2
                    ):
                        min_r, max_r = game_state.raise_bounds
                        raise_size = int(pot * (0.75 if eq >= 0.92 else 0.60))
                        return ActionRaise(max(min_r, min(raise_size, max_r)))
                    return ActionCall()
                return ActionFold()

            if ActionCheck in legal:
                if ActionRaise in legal:
                    if is_river and hand_strength in [
                        "three of a kind",
                        "straight",
                        "flush",
                        "full house",
                        "four of a kind",
                        "straight flush",
                    ]:
                        bet_threshold = 0.62
                    elif is_river and hand_strength == "two pair":
                        bet_threshold = 0.70
                    else:
                        bet_threshold = 0.78

                    if eq >= bet_threshold:
                        min_r, max_r = game_state.raise_bounds
                        bet_size = int(pot * 0.65) if is_river else int(pot * 0.7)
                        return ActionRaise(max(min_r, min(bet_size, max_r)))
                return ActionCheck()

            return ActionFold()


if __name__ == "__main__":
    run_bot(Player(), parse_args())
