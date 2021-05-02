import itertools
from collections import OrderedDict
from . import card

class LookupTable(object):
    """
    Number of Distinct Hand Values:

    Straight Flush   10
    Four of a Kind   156      [(13 choose 2) * (2 choose 1)]
    Full Houses      156      [(13 choose 2) * (2 choose 1)]
    Flush            1277     [(13 choose 5) - 10 straight flushes]
    Straight         10
    Three of a Kind  858      [(13 choose 3) * (3 choose 1)]
    Two Pair         858      [(13 choose 3) * (3 choose 2)]
    One Pair         2860     [(13 choose 4) * (4 choose 1)]
    High Card      + 1277     [(13 choose 5) - 10 straights]
    -------------------------
    TOTAL            7462

    Here we create a lookup table which maps:
        5 card hand's unique prime product => rank in range [1, 7462]

    Examples:
    * Royal flush (best hand possible)          => 1
    * 7-5-4-3-2 unsuited (worst hand possible)  => 7462
    """
    MAX_STRAIGHT_FLUSH  = 10
    MAX_FOUR_OF_A_KIND  = 166
    MAX_FULL_HOUSE      = 322
    MAX_FLUSH           = 1599
    MAX_STRAIGHT        = 1609
    MAX_THREE_OF_A_KIND = 2467
    MAX_TWO_PAIR        = 3325
    MAX_PAIR            = 6185
    MAX_HIGH_CARD       = 7462

    MAX_TO_RANK_CLASS = {
        MAX_STRAIGHT_FLUSH: 1,
        MAX_FOUR_OF_A_KIND: 2,
        MAX_FULL_HOUSE: 3,
        MAX_FLUSH: 4,
        MAX_STRAIGHT: 5,
        MAX_THREE_OF_A_KIND: 6,
        MAX_TWO_PAIR: 7,
        MAX_PAIR: 8,
        MAX_HIGH_CARD: 9
    }

    RANK_CLASS_TO_STRING = {
        1 : "Straight Flush",
        2 : "Four of a Kind",
        3 : "Full House",
        4 : "Flush",
        5 : "Straight",
        6 : "Three of a Kind",
        7 : "Two Pair",
        8 : "Pair",
        9 : "High Card"
    }

    def __init__(self):
        self.build()

    def build(self):
        """
        Builds member tables from scratch
        """
        self.flush = OrderedDict()
        self.unsuited = OrderedDict()
        self.build_flushes()  # this will call straights and high cards method + reuse some of the bit sequences
        self.build_multiples()

    def build_flushes(self):
        """
        Straight flushes and flushes.

        Lookup is done on 13 bit integer (2^13 > 7462):
        xxxbbbbb bbbbbbbb => integer hand index
        """
        # straight flushes in rank order
        straight_flushes = [
            7936, # int('0b1111100000000', 2), # royal flush
            3968, # int('0b111110000000', 2),
            1984, # int('0b11111000000', 2),
            992,  # int('0b1111100000', 2),
            496,  # int('0b111110000', 2),
            248,  # int('0b11111000', 2),
            124,  # int('0b1111100', 2),
            62,   # int('0b111110', 2),
            31,   # int('0b11111', 2),
            4111  # int('0b1000000001111', 2) # 5 high
        ]
        # now we'll dynamically generate all the other
        # flushes (including straight flushes)
        flushes = []
        gen = next_word(int('0b11111', 2))

        # 1277 = number of high cards
        # 1277 + len(str_flushes) is number of hands with all cards unique rank
        for i in range(1277 + len(straight_flushes) - 1): # we also iterate over SFs
            # pull the next flush pattern from our generator
            f = next(gen)
            # if this flush matches perfectly any
            # straight flush, do not add it
            notSF = True
            for sf in straight_flushes:
                # if f XOR sf == 0, then bit pattern 
                # is same, and we should not add
                if not f ^ sf:
                    notSF = False
            if notSF:
                flushes.append(f)

        # we started from the lowest straight pattern, now we want to start ranking from
        # the most powerful hands, so we reverse
        flushes.reverse()

        # now add to the lookup map:
        # start with straight flushes and the rank of 1
        # since theyit is the best hand in poker
        # rank 1 = Royal Flush!
        rank = 1
        for sf in straight_flushes:
            _, product = card.product_from_rankbits(sf)
            self.flush[product] = rank
            rank += 1

        # we start the counting for flushes on max full house, which
        # is the worst rank that a full house can have (2,2,2,3,3)
        rank = LookupTable.MAX_FULL_HOUSE + 1
        for f in flushes:
            _, product = card.product_from_rankbits(f)
            self.flush[product] = rank
            rank += 1

        # we can reuse these bit sequences for straights
        # and high cards since they are inherently related
        # and differ only by context 
        self.build_straight_and_highcards(straight_flushes, flushes)

    def build_straight_and_highcards(self, straights, highcards):
        """
        Unique five card sets. Straights and highcards.
        Reuses bit sequences from flush calculations.
        """
        rank = LookupTable.MAX_FLUSH + 1
        for s in straights:
            _, product = card.product_from_rankbits(s)
            self.unsuited[product] = rank
            rank += 1
        rank = LookupTable.MAX_PAIR + 1
        for h in highcards:
            _, product = card.product_from_rankbits(h)
            self.unsuited[product] = rank
            rank += 1

    def build_multiples(self):
        """
        Pair, Two Pair, Three of a Kind, Full House, and 4 of a Kind.
        """
        backwards_ranks = list(range(13 - 1, -1, -1))
        # 1) Four of a Kind
        rank = LookupTable.MAX_STRAIGHT_FLUSH + 1
        # for each choice of a set of four rank
        for i in backwards_ranks:
            # and for each possible kicker rank
            # XXX list hack, was:
            # kickers = backwards_ranks[:]
            kickers = list(backwards_ranks)
            kickers.remove(i)
            for k in kickers:
                product = card.PRIMES[i]**4 * card.PRIMES[k]
                self.unsuited[product] = rank
                rank += 1

        # 2) Full House
        rank = LookupTable.MAX_FOUR_OF_A_KIND + 1

        # for each three of a kind
        for i in backwards_ranks:
            # and for each choice of pair rank
            # XXX list hack, was:
            # pairranks = backwards_ranks[:]
            pairranks = list(backwards_ranks)
            pairranks.remove(i)
            for pr in pairranks:
                product = card.PRIMES[i]**3 * card.PRIMES[pr]**2
                self.unsuited[product] = rank
                rank += 1

        # 3) Three of a Kind
        rank = LookupTable.MAX_STRAIGHT + 1

        # pick three of one rank
        for r in backwards_ranks:
            # XXX list hack, was:
            # kickers = backwards_ranks[:]
            kickers = list(backwards_ranks)
            kickers.remove(r)
            gen = itertools.combinations(kickers, 2)
            for kickers in gen:
                c1, c2 = kickers
                product = card.PRIMES[r]**3 * card.PRIMES[c1] * card.PRIMES[c2]
                self.unsuited[product] = rank
                rank += 1

        # 4) Two Pair
        rank = LookupTable.MAX_THREE_OF_A_KIND + 1
        tpgen = itertools.combinations(backwards_ranks, 2)
        for tp in tpgen:
            pair1, pair2 = tp
            # XXX list hack, was:
            # kickers = backwards_ranks[:]
            kickers = list(backwards_ranks)
            kickers.remove(pair1)
            kickers.remove(pair2)
            for kicker in kickers:
                product = card.PRIMES[pair1]**2 * card.PRIMES[pair2]**2 * card.PRIMES[kicker]
                self.unsuited[product] = rank
                rank += 1

        # 5) Pair
        rank = LookupTable.MAX_TWO_PAIR + 1

        # choose a pair
        for pairrank in backwards_ranks:
            # XXX list hack, was:
            # kickers = backwards_ranks[:]
            kickers = list(backwards_ranks)
            kickers.remove(pairrank)
            kgen = itertools.combinations(kickers, 3)
            for kickers in kgen:
                k1, k2, k3 = kickers
                product = card.PRIMES[pairrank]**2 * card.PRIMES[k1] \
                        * card.PRIMES[k2] * card.PRIMES[k3]
                self.unsuited[product] = rank
                rank += 1


class LookupTableThreeCards(object):
    """
    Map of draws when having three cards (flop)
    Used to evalute when the player has straight flush, flush, straight backdoor

    TODO: evaluate when player has trips or one pair to get a poker/full
    """
    #all possible combos that can yield each type of hand after the river

    """
       Number of Distinct Combos that can yield the mentioned hand:

       Straight Flush   10 = 5C3 * 10 Some of them generate the same straight, so 10 in total
       Four of a Kind   169 = 13 + 13*12  
       Full Houses      169 = 13 + 13*12  
       Flush            222 = 13C3 - (5C3 * 10) +  Repetitions from straight flush draws
       Straight         10 = 5C3 * 10 Some of them generate the same straight, so 10 in total
       Three of a Kind  442 = 13*12 + 13C3    
       Two Pair         442 = 13*12 + 13C3
       One Pair         286 = 13C3      
       -------------------------
       TOTAL            1750

       There are a total of 1840 combos which can improve the current 3 cards hand
       Notice we discard high card, because it is not an interesting case
       We also discard combinations of suits because if they are not suited it is not important
       the suit combination
       
       this is a sort of qualification for the existent combos, base on their improvement potential
    """

    MAX_STRAIGHT_FLUSH = 10
    MAX_FOUR_OF_A_KIND = 179
    MAX_FULL_HOUSE = 348
    MAX_FLUSH = 570
    MAX_STRAIGHT = 580
    MAX_THREE_OF_A_KIND = 1022
    MAX_TWO_PAIR = 1464
    MAX_PAIR = 1750

    def __init__(self):
        self.build()

    def build(self):
        """
        Builds member tables from scratch
        """
        self.flush = OrderedDict()
        self.unsuited = OrderedDict()
        self.build_flushes()  # this will call straights and high cards method + reuse some of the bit sequences
        self.build_multiples()

    def build_flushes(self):
        """
        Straight flushes and flushes.

        Lookup is done on 13 bit integer (2^13 > 7462):
        xxxbbbbb bbbbbbbb => integer hand index
        """
        # straight flushes in rank order

        #we start creating the sequence of cards that draw the same straight flush
        sequence = [7] #7 = int('0b111',2)
        gen = next_word(sequence[0])

        for i in range(9):
            f = next(gen)
            sequence.append(f)

        #Ordering from top to bottom
        sequence.reverse()

        straight_flushes = []
        for i in range(8,-1,-1):
            for a in sequence:
                straight_flushes.append(a << i)

        gen = next_word(int('0b1000000000011',2))
        straight_flushes.append(int('0b1000000000011',2))
        for i in range(5):
            f = next(gen)
            straight_flushes.append(f)

        gen = next_word(int('0b111', 2))
        straight_flushes.append(int('0b111', 2))
        for i in range(3):
            f = next(gen)
            straight_flushes.append(f)

        flushes = []
        gen = next_word(int('0b111',2))
        for i in range(285):
            f = next(gen)
            flushes.append(f)

        rank = 1
        co = 0
        for sf in straight_flushes:
            current_cards, product = card.product_from_rankbits(sf)
            exist_key = bool(self.flush.get(product))
            if exist_key:
                self.flush[product].append(rank)
            else:
                self.flush[product] = [rank]
            #TODO: Compute the outs to complete the draw
            if co == 9:
                rank += 1
                co = 0
            else:
                co += 1

        # from flushes list we remove those which belong to straight flush draws
        set_dif = set(flushes) - set(straight_flushes)
        flushes = list(set_dif)
        flushes.sort()
        flushes.reverse()

        rank = LookupTableThreeCards.MAX_FULL_HOUSE + 1
        for f in flushes:
            current_cards, product = card.product_from_rankbits(f)
            self.flush[product] = rank
            rank += 1

        self.build_straights(straight_flushes)

    def build_straights(self, straights):
        """
        Unique five card sets. Straights and highcards.
        Reuses bit sequences from flush calculations.
        """
        rank = LookupTableThreeCards.MAX_FLUSH + 1
        co = 0
        for sf in straights:
            current_cards, product = card.product_from_rankbits(sf)
            exist_key = bool(self.unsuited.get(product))
            if exist_key:
                self.unsuited[product].append(rank)
            else:
                self.unsuited[product] = [rank]
            # TODO: Compute the outs to complete the draw
            if co == 9:
                rank += 1
                co = 0
            else:
                co += 1

    def build_multiples(self):
        """
        Pair, Two Pair, Three of a Kind, Full House, and 4 of a Kind.
        """
        backwards_ranks = list(range(13 - 1, -1, -1))
        # 1) Four of a Kind
        rank = LookupTableThreeCards.MAX_STRAIGHT_FLUSH + 1
        # considering the current hand is three of a kind
        for i in backwards_ranks:
            product = card.PRIMES[i]**3
            exist_key = bool(self.unsuited.get(product))
            if exist_key:
                self.unsuited[product].append(rank)
            else:
                self.unsuited[product] = [rank]
            rank += 1

        # considering the current hand is a pair
        for i in backwards_ranks:
            # and for each possible kicker rank
            # XXX list hack, was:
            # kickers = backwards_ranks[:]
            kickers = list(backwards_ranks)
            kickers.remove(i)
            for k in kickers:
                product = card.PRIMES[i]**2 * card.PRIMES[k]
                exist_key = bool(self.unsuited.get(product))
                if exist_key:
                    self.unsuited[product].append(rank)
                else:
                    self.unsuited[product] = [rank]
                rank += 1

        # 2) Full House
        rank = LookupTableThreeCards.MAX_FOUR_OF_A_KIND + 1

        # considering the current hand is three of a kind
        for i in backwards_ranks:
            product = card.PRIMES[i] ** 3
            exist_key = bool(self.unsuited.get(product))
            if exist_key:
                self.unsuited[product].append(rank)
            else:
                self.unsuited[product] = [rank]
            rank += 1

        # # considering the current hand is a pair
        for i in backwards_ranks:
            # and for each possible kicker rank
            # XXX list hack, was:
            # kickers = backwards_ranks[:]
            kickers = list(backwards_ranks)
            kickers.remove(i)
            for k in kickers:
                product = card.PRIMES[i] ** 2 * card.PRIMES[k]
                exist_key = bool(self.unsuited.get(product))
                if exist_key:
                    self.unsuited[product].append(rank)
                else:
                    self.unsuited[product] = [rank]
                rank += 1

        # 3) Three of a Kind
        rank = LookupTableThreeCards.MAX_STRAIGHT + 1

        # considering the current hand is three of a kind

        # for i in backwards_ranks:
        #     product = card.PRIMES[i] ** 3
        #     exist_key = bool(self.unsuited.get(product))
        #     if exist_key:
        #         self.unsuited[product].append(rank)
        #     else:
        #         self.unsuited[product] = [rank]
        #     rank += 1

        # # considering the current hand is a pair
        for i in backwards_ranks:
            # and for each possible kicker rank
            # XXX list hack, was:
            # kickers = backwards_ranks[:]
            kickers = list(backwards_ranks)
            kickers.remove(i)
            for k in kickers:
                product = card.PRIMES[i] ** 2 * card.PRIMES[k]
                exist_key = bool(self.unsuited.get(product))
                if exist_key:
                    self.unsuited[product].append(rank)
                else:
                    self.unsuited[product] = [rank]
                rank += 1

        # considering the current does not have any combination (highcard only)
        gen = itertools.combinations(backwards_ranks,3)
        for r in gen:
            c1, c2, c3 = r
            product = card.PRIMES[c1] * card.PRIMES[c2] * card.PRIMES[c3]
            exist_key = bool(self.unsuited.get(product))
            if exist_key:
                self.unsuited[product].append(rank)
            else:
                self.unsuited[product] = [rank]
            rank += 1

        # 4) Two Pairs
        rank = LookupTableThreeCards.MAX_THREE_OF_A_KIND + 1

        # pick three of one rank
        for r in backwards_ranks:
            # XXX list hack, was:
            # kickers = backwards_ranks[:]
            kickers = list(backwards_ranks)
            kickers.remove(r)
            for k in kickers:
                product = card.PRIMES[i] ** 2 * card.PRIMES[k]
                exist_key = bool(self.unsuited.get(product))
                if exist_key:
                    self.unsuited[product].append(rank)
                else:
                    self.unsuited[product] = [rank]
                rank += 1

        # considering the current does not have any combination (highcard only)
        gen = itertools.combinations(backwards_ranks, 3)
        for r in gen:
            c1, c2, c3 = r
            product = card.PRIMES[c1] * card.PRIMES[c2] * card.PRIMES[c3]
            exist_key = bool(self.unsuited.get(product))
            if exist_key:
                self.unsuited[product].append(rank)
            else:
                self.unsuited[product] = [rank]
            rank += 1

        # 5) One Pair
        rank = LookupTableThreeCards.MAX_TWO_PAIR + 1

        # considering the current does not have any combination (highcard only)
        gen = itertools.combinations(backwards_ranks, 3)
        for r in gen:
            c1, c2, c3 = r
            product = card.PRIMES[c1] * card.PRIMES[c2] * card.PRIMES[c3]
            exist_key = bool(self.unsuited.get(product))
            if exist_key:
                self.unsuited[product].append(rank)
            else:
                self.unsuited[product] = [rank]
            rank += 1


    def straight_outs(self, cards, top_card):
        """
        :param cards: Current 3 cards of the player (given in card symbols)
        :param top_card: the highest card of the straight we are looking for (rankbit)
        :return: symbol (in bitrank representation) of the cards the player needs to run
        """


class LookupTableFourCards(object):
    """
    Map of draws when having four cards (turn)
    Used to evaluate draws after the turn

    """
    # all possible combos that can yield each type of hand after the river

    """
       Number of Distinct Combos that can yield the mentioned hand:

       Straight Flush   10 = 5C4 * 10 Some of them generate the same straight, so 10 in total
       Four of a Kind   156 = [13C2 * 2C1]  
       Full Houses      312 = [13C2 * 2C1] + [13C2 * 2C1]  
       Flush            674 = 13C4 - (5C4 * 10) +  Repetitions from straight flush draws
       Straight         10 = 5C4 * 10 Some of them generate the same straight, so 10 in total
       Three of a Kind  858 = [13C3 * 3C1]   
       Two Pair         858 = [13C3 * 3C1]
       One Pair         715 = 13C4      
       -------------------------
       TOTAL            3593

       There are a total of 3593 combos which can improve the current 4 cards hand
       Notice we discard high card, because it is not an interesting case
       We also discard combinations of suits because if they are not suited it is not important
       the suit combination

       this is a sort of qualification for the existent combos, base on their improvement potential
    """

    MAX_STRAIGHT_FLUSH = 10
    MAX_FOUR_OF_A_KIND = 166
    MAX_FULL_HOUSE = 478
    MAX_FLUSH = 1152
    MAX_STRAIGHT = 1162
    MAX_THREE_OF_A_KIND = 2020
    MAX_TWO_PAIR = 2878
    MAX_PAIR = 3593

    def __init__(self):
        self.build()

    def build(self):
        """
        Builds member tables from scratch
        """
        self.flush = OrderedDict()
        self.unsuited = OrderedDict()
        self.build_flushes()  # this will call straights and high cards method + reuse some of the bit sequences
        self.build_multiples()

    def build_flushes(self):
        """
        Straight flushes and flushes.

        Lookup is done on 13 bit integer (2^13 > 7462):
        xxxbbbbb bbbbbbbb => integer hand index
        """
        # straight flushes in rank order

        # we start creating the sequence of cards that draw the same straight flush
        sequence = [7]  # 7 = int('0b111',2)
        gen = next_word(sequence[0])

        for i in range(4):
            f = next(gen)
            sequence.append(f)

        # Ordering from top to bottom
        sequence.reverse()

        straight_flushes = []
        for i in range(8, -1, -1):
            for a in sequence:
                straight_flushes.append(a << i)

        gen = next_word(int('0b1000000000111', 2))
        straight_flushes.append(int('0b1000000000111', 2))
        for i in range(3):
            f = next(gen)
            straight_flushes.append(f)

        straight_flushes.append(int('0b1111', 2))


        flushes = []
        gen = next_word(int('0b1111', 2))
        for i in range(714):
            f = next(gen)
            flushes.append(f)

        rank = 1
        co = 0
        for sf in straight_flushes:
            current_cards, product = card.product_from_rankbits(sf)
            exist_key = bool(self.flush.get(product))
            if exist_key:
                self.flush[product].append(rank)
            else:
                self.flush[product] = [rank]
            # TODO: Compute the outs to complete the draw
            if co == 9:
                rank += 1
                co = 0
            else:
                co += 1

        # from flushes list we remove those which belong to straight flush draws
        set_dif = set(flushes) - set(straight_flushes)
        flushes = list(set_dif)
        flushes.sort()
        flushes.reverse()

        rank = LookupTableFourCards.MAX_FULL_HOUSE + 1
        for f in flushes:
            current_cards, product = card.product_from_rankbits(f)
            self.flush[product] = rank
            rank += 1

        self.build_straights(straight_flushes)

    def build_straights(self, straights):
        """
        Unique five card sets. Straights and highcards.
        Reuses bit sequences from flush calculations.
        """
        rank = LookupTableFourCards.MAX_FLUSH + 1
        co = 0
        for sf in straights:
            current_cards, product = card.product_from_rankbits(sf)
            exist_key = bool(self.unsuited.get(product))
            if exist_key:
                self.unsuited[product].append(rank)
            else:
                self.unsuited[product] = [rank]
            # TODO: Compute the outs to complete the draw
            if co == 9:
                rank += 1
                co = 0
            else:
                co += 1

    def build_multiples(self):
        """
        Pair, Two Pair, Three of a Kind, Full House, and 4 of a Kind.
        """
        backwards_ranks = list(range(13 - 1, -1, -1))
        # 1) Four of a Kind
        rank = LookupTableFourCards.MAX_STRAIGHT_FLUSH + 1
        # considering the current hand is three of a kind
        for i in backwards_ranks:
            # and for each possible kicker rank
            # XXX list hack, was:
            # kickers = backwards_ranks[:]
            kickers = list(backwards_ranks)
            kickers.remove(i)
            for k in kickers:
                product = card.PRIMES[i] ** 3 * card.PRIMES[k]
                exist_key = bool(self.unsuited.get(product))
                if exist_key:
                    self.unsuited[product].append(rank)
                else:
                    self.unsuited[product] = [rank]
                rank += 1


        # 2) Full House
        rank = LookupTableFourCards.MAX_FOUR_OF_A_KIND + 1

        # considering the current hand is three of a kind
        for i in backwards_ranks:
            # and for each possible kicker rank
            # XXX list hack, was:
            # kickers = backwards_ranks[:]
            kickers = list(backwards_ranks)
            kickers.remove(i)
            for k in kickers:
                product = card.PRIMES[i] ** 3 * card.PRIMES[k]
                exist_key = bool(self.unsuited.get(product))
                if exist_key:
                    self.unsuited[product].append(rank)
                else:
                    self.unsuited[product] = [rank]
                rank += 1

        # considering the current hand is two pairs
        for i in backwards_ranks:
            # and for each possible kicker rank
            # XXX list hack, was:
            # kickers = backwards_ranks[:]
            kickers = list(backwards_ranks)
            kickers.remove(i)
            for k in kickers:
                product = card.PRIMES[i] ** 2 * card.PRIMES[k] ** 2
                exist_key = bool(self.unsuited.get(product))
                if exist_key:
                    self.unsuited[product].append(rank)
                else:
                    self.unsuited[product] = [rank]
                rank += 1

        # 3) Three of a Kind
        rank = LookupTableFourCards.MAX_STRAIGHT + 1


        # # considering the current hand is a pair
        for pairrank in backwards_ranks:
            # XXX list hack, was:
            # kickers = backwards_ranks[:]
            kickers = list(backwards_ranks)
            kickers.remove(pairrank)
            kgen = itertools.combinations(kickers, 2)
            for kickers in kgen:
                k1, k2 = kickers
                product = card.PRIMES[pairrank]**2 * card.PRIMES[k1] * card.PRIMES[k2]
                exist_key = bool(self.unsuited.get(product))
                if exist_key:
                    self.unsuited[product].append(rank)
                else:
                    self.unsuited[product] = [rank]
                rank += 1


        # 4) Two Pairs
        rank = LookupTableFourCards.MAX_THREE_OF_A_KIND + 1

        # # considering the current hand is a pair
        for pairrank in backwards_ranks:
            # XXX list hack, was:
            # kickers = backwards_ranks[:]
            kickers = list(backwards_ranks)
            kickers.remove(pairrank)
            kgen = itertools.combinations(kickers, 2)
            for kickers in kgen:
                k1, k2 = kickers
                product = card.PRIMES[pairrank] ** 2 * card.PRIMES[k1] * card.PRIMES[k2]
                exist_key = bool(self.unsuited.get(product))
                if exist_key:
                    self.unsuited[product].append(rank)
                else:
                    self.unsuited[product] = [rank]
                rank += 1

        # 5) One Pair
        rank = LookupTableFourCards.MAX_TWO_PAIR + 1

        # considering the current does not have any combination (highcard only)
        gen = itertools.combinations(backwards_ranks, 4)
        for r in gen:
            c1, c2, c3, c4 = r
            product = card.PRIMES[c1] * card.PRIMES[c2] * card.PRIMES[c3] * card.PRIMES[c4]
            exist_key = bool(self.unsuited.get(product))
            if exist_key:
                self.unsuited[product].append(rank)
            else:
                self.unsuited[product] = [rank]
            rank += 1


def next_word(bits):
    """
    Gets the so-called "next lexographic bit sequence" from a starting word :bits
    Bit hack from here:

      http://www-graphics.stanford.edu/~seander/bithacks.html#NextBitPermutation

    Generator even does this in poker order rank so no need to sort when done! Perfect.
    """
    # XXX tidy
    t = (bits | (bits - 1)) + 1
    # XXX math hack - '/' => '//'
    w = t | ((((t & -t) // (bits & -bits)) >> 1) - 1)
    yield w
    while True:
        t = (w | (w - 1)) + 1
        # XXX math hack - '/' => '//'
        w = t | ((((t & -t) // (w & -w)) >> 1) - 1)
        yield w
