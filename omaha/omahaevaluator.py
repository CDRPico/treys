from treys.evaluator import Evaluator
from treys.lookup import LookupTable
import itertools

#Here I'm gonna evaluate all omaha and omaha five hands
#We need to consider after flop we pick up two cards from poker hand (all possible combinations)
#repeat the evaluation for turn and river action
#create also methods to evaluate how the hand can get upgraded with future cards


class OmahaEvaluator(Evaluator):
    """Evaluate the strenght of hands considering its parent class and the
    new features are that hands have 8, 9 and 10 cards at flop, turn and rive"""

    def __init__(self):
        super().__init__()
        self.hand_size_map = {
            5: self._five,
            6: self._six,
            7: self._seven,
            8: self._eightnineten,
            9: self._eightnineten,
            10: self._eightnineten
        }

    def _eightnineten(self, cards):
        """
        :param cards:
        :return: Performs all possible combinations of two player card (from 5)
        with the current 3 in flop, then returns the current best player's hand
        """
        minimum = LookupTable.MAX_HIGH_CARD
        all2cardscombos = itertools.combinations(cards[:5], 2)
        all2cardscombos = list(all2cardscombos)
        all2cardscombos = [list(a) for a in all2cardscombos]
        all5cardscombos = [a + cards[5:] for a in all2cardscombos]
        for combo in all5cardscombos:
            score = self._five(combo)
            if score < minimum:
                minimum = score
        return minimum
