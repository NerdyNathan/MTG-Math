import numpy as np
import random
from matplotlib import pyplot as plt
import sys

sys.stdout = open('outputfile.txt', 'w')

# Note: I don't have a lot of experience with Python yet, so suggestions for improving the code are welcome!

relevant_ranks = ['bronze', 'silver', 'gold', 'platinum', 'diamond']
DEBUG = False


def log(s):
    if DEBUG:
        print(s)


steps_gained_with_win = {
    'bronze': 2,
    'silver': 2,
    'gold': 2,
    'platinum': 1,
    'diamond': 1
}

steps_lost_with_loss = {
    'bronze': 0,
    'silver': 1,
    'gold': 1,
    'platinum': 1,
    'diamond': 1
}


def expected_games_without_tier_protection(game_win_prob, _rank, _bestof):
    """The setting without tier protection is relatively easy. For bestof = 1, this function gives the exact expected
    number of games to reach the next rank in best-of-one. For bestof = 3, this function gives an approximation for
    the expected number of games to reach the next rank in best-of-three. This approximation assumes that any match
    takes 2.5 games.

    To determine this, this function creates a matrix to represent the system of equations of the form Ax=b Let x[n]
    represent the expected number of games to hit the next rank from state n For non-endpoint states n, it holds that
    x[n] = winrate * (1 + x[n+steps_gained_with_win]) + lossrate * (1 + x[n-steps_lost_with_loss]) This implies that
    x[n] - winrate * x[n+steps_gained_with_win] - lossrate * x[n-steps_lost_with_loss] = 1 A matrix is created with
    these numbers, making appropriate adjustments for endpoint states, then solved

    Parameters -
        game_win_prob: Probability to win any game
        rank: the rank we're interested in, e.g., 'silver'
        bestof: must be 1 or 3

    Returns - a number that represents the expected number of games to reach the next rank
    """
    multiplier = 1
    winrate = game_win_prob
    if _bestof == 3:
        multiplier = 2
        winrate = game_win_prob * game_win_prob + 2 * game_win_prob * game_win_prob * (1 - game_win_prob)
    lossrate = 1 - winrate

    steps_per_rank = {k: v * 4 for k, v in STEP_PER_TIER.items()}
    A = np.zeros((steps_per_rank[_rank], steps_per_rank[_rank]))
    b = np.ones(steps_per_rank[_rank])

    for n in range(0, steps_per_rank[_rank]):
        A[n, n] = 1
        A[n, max(0, n - multiplier * steps_lost_with_loss[_rank])] -= lossrate
        if n + multiplier * steps_gained_with_win[_rank] < steps_per_rank[_rank]:
            A[n, n + multiplier * steps_gained_with_win[_rank]] -= winrate

    x = np.linalg.solve(A, b)
    if _bestof == 1:
        return x[0]
    if _bestof == 3:
        return x[0] * 2.5


def give_index(_rank, tier, step, protection):
    """The challenging aspect with tier protection is turning the three-dimensional state space into a single
    dimension, as required for solving the LP There surely is a better way to do this, but my convoluted method
    should at least work State is given as (tier, step, protection) For steps>=2, protection must be 0 For step 0 or
    step 1, protection can be 3, 2, 1, or 0. (Step 1, protection 3 never happens in practice. Also, step 1,
    protection 1 is equivalent to step 1, protection 0. They are included to allow fewer exceptions later in the
    code.) Consider Gold rank as an example. Index 0 is (4, 0, 0) Index 1 is (4, 1, 0) ... Index 5 is (4, 5,
    0) Index 6 is (3, 0, 0) Index 7 is (3, 1, 0) ... Index 23 is (1, 5, 0) THEN Index 24 is (3, 0, 3) Index 25 is (3,
    0, 2) Index 26 is (3, 0, 1) Index 27 is (2, 0, 3) Index 28 is (2, 0, 2) ... Index 33 is (3, 1, 3) Index 34 is (3,
    1, 2) Index 35 is (3, 1, 1) ... Index 41 is (1, 1, 1)
    """
    if protection == 0:
        return (4 - tier) * STEP_PER_TIER[_rank] + step
    if protection > 0 and step == 0:
        return 4 * STEP_PER_TIER[_rank] + (3 - tier) * 3 + 3 - protection
    if protection > 0 and step == 1:
        return 4 * STEP_PER_TIER[_rank] + 9 + (3 - tier) * 3 + 3 - protection


def give_tier(index):
    if index < 4 * STEP_PER_TIER[rank]:
        return 4 - (index // STEP_PER_TIER[rank])
    if 4 * STEP_PER_TIER[rank] <= index < 4 * STEP_PER_TIER[rank] + 9:
        return 3 - (index - 4 * STEP_PER_TIER[rank]) // 3
    if index >= 4 * STEP_PER_TIER[rank] + 9:
        return 3 - (index - (4 * STEP_PER_TIER[rank] + 9)) // 3


def give_step(index):
    if index < 4 * STEP_PER_TIER[rank]:
        return index % STEP_PER_TIER[rank]
    if 4 * STEP_PER_TIER[rank] <= index < 4 * STEP_PER_TIER[rank] + 9:
        return 0
    if index >= 4 * STEP_PER_TIER[rank] + 9:
        return 1


def give_protection(index):
    if index < 4 * STEP_PER_TIER[rank]:
        return 0
    if 4 * STEP_PER_TIER[rank] <= index < 4 * STEP_PER_TIER[rank] + 9:
        return 3 - ((index - 4 * STEP_PER_TIER[rank]) % 3)
    if index >= 4 * STEP_PER_TIER[rank] + 9:
        return 3 - ((index - (4 * STEP_PER_TIER[rank] + 9)) % 3)


def describe_state(index):
    tier = str(give_tier(index))
    step = str(give_step(index))
    protection = str(give_protection(index))
    return "the state with tier " + tier + ", step " + step + ", and protection " + protection


def expected_games_with_tier_protection(game_win_prob, _rank, _bestof):
    """The setting with tier protection is more involved. For bestof = 1, this function gives the exact expected
    number of games to reach the next rank in best-of-one. For bestof = 3, this function gives an approximation for
    the expected number of games to reach the next rank in best-of-three. This approximation assumes that any match
    takes 2.5 games.

    To determine this, this function creates a matrix to represent the system of equations of the form Ax=b

    Parameters -
        game_win_prob: Probability to win any game
        rank: the rank we're interested in, e.g., 'silver'
        bestof: must be 1 or 3

    Returns - a number that represents the expected number of games to reach the next rank
    """
    multiplier = 1
    winrate = game_win_prob
    protection = 3
    if _bestof == 3:
        multiplier = 2
        winrate = game_win_prob * game_win_prob + 2 * game_win_prob * game_win_prob * (1 - game_win_prob)
        protection = 1
    lossrate = 1 - winrate

    steps_per_rank = {k: v * 4 for k, v in STEP_PER_TIER.items()}
    total_number_of_states = steps_per_rank[_rank] + 3 * 3 + 3 * 3
    A = np.zeros((total_number_of_states, total_number_of_states))
    b = np.ones(total_number_of_states)

    for index in range(0, total_number_of_states):
        log("\n")
        log("Index number " + str(
            give_index(_rank, give_tier(index), give_step(index), give_protection(index))) + " is " + describe_state(
            index))
        A[index, index] = 1
        if index + multiplier * steps_gained_with_win[_rank] < steps_per_rank[_rank]:
            # This means that a win won't advance you to the next rank and that you don't have protection
            if give_step(index) + multiplier * steps_gained_with_win[_rank] < STEP_PER_TIER[_rank]:
                # With a win, move to the next step in the same tier
                A[index, index + multiplier * steps_gained_with_win[_rank]] -= winrate
                log("--We take off winrate from " + describe_state(index + multiplier * steps_gained_with_win[_rank]))
            if give_step(index) + multiplier * steps_gained_with_win[_rank] >= STEP_PER_TIER[_rank]:
                # With a win, move to the next tier with protection, unless we're in Bronze Bo3 or Silver Bo3 and
                # would end up in step 2+ with unnecessary protection
                new_step_with_win = give_step(index) + multiplier * steps_gained_with_win[_rank] - STEP_PER_TIER[_rank]
                proper_protection = protection if new_step_with_win < 2 else 0
                A[index, give_index(_rank, give_tier(index) - 1, new_step_with_win, proper_protection)] -= winrate
                log("--We take off winrate from " + describe_state(
                    give_index(_rank, give_tier(index) - 1, new_step_with_win, proper_protection)))
            A[index, max(0, index - multiplier * steps_lost_with_loss[_rank])] -= lossrate
            log("--We take off lossrate from " + describe_state(
                max(0, index - multiplier * steps_lost_with_loss[_rank])))
        if index + multiplier * steps_gained_with_win[_rank] >= steps_per_rank[_rank] and give_protection(index) == 0:
            # This means that a win will advance you to the next rank
            A[index, max(0, index - multiplier * steps_lost_with_loss[_rank])] -= lossrate
            log("--We take off lossrate from " + describe_state(
                max(0, index - multiplier * steps_lost_with_loss[_rank])))
        if give_protection(index) > 0:
            # This means that you have protection
            new_step_with_win = give_step(index) + multiplier * steps_gained_with_win[_rank]
            new_protection_with_win = 0 if new_step_with_win >= 2 else give_protection(index) - 1
            if new_step_with_win < STEP_PER_TIER[_rank]:
                # With a win, move to the next step in the same tier
                A[index, give_index(_rank, give_tier(index), new_step_with_win, new_protection_with_win)] -= winrate
                log("--We take off winrate from " + describe_state(
                    give_index(_rank, give_tier(index), new_step_with_win, new_protection_with_win)))
            if new_step_with_win >= STEP_PER_TIER[_rank]:
                # This should only happen in Bronze or Silver Bo3, but with a win, move to the next tier or rank
                new_step_with_win = new_step_with_win - STEP_PER_TIER[_rank]
                if give_tier(index) > 1:
                    proper_protection = protection if new_step_with_win < 2 else 0
                    A[index, give_index(_rank, give_tier(index) - 1, new_step_with_win, proper_protection)] -= winrate
                    log("--We take off winrate from " + describe_state(
                        give_index(_rank, give_tier(index) - 1, new_step_with_win, proper_protection)))
            A[index, give_index(_rank, give_tier(index),
                                max(0, give_step(index) - multiplier * steps_lost_with_loss[_rank]),
                                give_protection(index) - 1)] -= lossrate
            log("--We take off lossrate from " + describe_state(
                give_index(_rank, give_tier(index), max(0, give_step(index) - multiplier * steps_lost_with_loss[_rank]),
                           give_protection(index) - 1)))

    x = np.linalg.solve(A, b)
    if _bestof == 1:
        return x[0]
    if _bestof == 3:
        return x[0] * 2.5


def run_simulation(game_win_prob, _rank, _bestof):
    """Simulation approach, with tier protection. For bestof = 1, this approximates the expected number of games to
    reach the next rank in best-of-one. For bestof = 3, this approximates the expected number of games to reach the
    next rank in best-of-three. The approximation accurately takes into account that the expected number of games per
    match is different for matches won and matches lost.

    Parameters -
        game_win_prob: Probability to win any game
        rank: the rank we're interested in, e.g., 'silver'
        bestof: must be 1 or 3

    Returns - a number that approximates the expected number of games to reach the next rank
    """
    games_per_simulation = []
    for _ in range(5000):
        games_per_simulation.append(simulate_rank(_rank, _bestof, game_win_prob))

    return np.mean(games_per_simulation)


def simulate_rank(_rank, _bestof, game_win_prob):
    multiplier = 1
    winrate = game_win_prob
    protection = 3
    if _bestof == 3:
        multiplier = 2
        winrate = game_win_prob * game_win_prob + 2 * game_win_prob * game_win_prob * (1 - game_win_prob)
        protection = 1

    curr_tier = 4
    curr_step = curr_protection = match_count = curr_wins = curr_losses = 0
    while True:
        match_count += 1
        if random.random() < winrate:
            match_win = True
            curr_wins += 1
        else:
            match_win = False
            curr_losses += 1
        if (match_win and curr_tier == 1
                and curr_step + multiplier * steps_gained_with_win[_rank] >= STEP_PER_TIER[_rank]):
            # Advance to the next rank
            break
        elif (match_win and curr_tier > 1
              and curr_step + multiplier * steps_gained_with_win[_rank] >= STEP_PER_TIER[_rank]):
            # Move to the next tier with protection
            curr_tier -= 1
            curr_protection = protection
            curr_step = curr_step + multiplier * steps_gained_with_win[_rank] - STEP_PER_TIER[_rank]
        elif match_win and curr_step + multiplier * steps_gained_with_win[_rank] < STEP_PER_TIER[_rank]:
            # Move up steps in the same tier
            curr_step += multiplier * steps_gained_with_win[_rank]
            curr_protection -= 1
        elif ((not match_win)
              and curr_step < multiplier * steps_lost_with_loss[_rank] and curr_protection <= 0 and curr_tier < 4):
            # Fall back a tier
            curr_step = STEP_PER_TIER[_rank] - multiplier * steps_lost_with_loss[_rank]
            curr_tier += 1
        elif (not match_win) and curr_step < multiplier * steps_lost_with_loss[_rank] and curr_protection > 0:
            # Remain at the start of the tier with reduced protection
            curr_protection -= 1
            curr_step = 0
        elif (not match_win) and curr_step >= multiplier * steps_lost_with_loss[_rank]:
            # Move down steps in the same tier
            curr_step -= multiplier * steps_lost_with_loss[_rank]
            curr_protection -= 1

    if _bestof == 1:
        return match_count

    games_per_match_won = (2 * game_win_prob * game_win_prob + 3 * 2 * game_win_prob * game_win_prob * (
            1 - game_win_prob)) / winrate
    games_per_match_lost = (2 * (1 - game_win_prob) * (1 - game_win_prob) + 3 * 2 * (1 - game_win_prob) * (
            1 - game_win_prob) * game_win_prob) / (1 - winrate)
    return curr_wins * games_per_match_won + curr_losses * games_per_match_lost


# Since everything checked out, let's get the Preseason 2 results for Limited.
STEP_PER_TIER = {
    'bronze': 4,
    'silver': 5,
    'gold': 5,
    'platinum': 5,
    'diamond': 5
}

# First, output the Limited results as semicolon separated values
win_probs = [0.4 + i * 2 / 100 for i in range(0, 16)]
print("LIMITED win_prob; bronze to silver; silver to gold; gold to platinum; platinum to diamond; diamond to mythic")
for win_prob in win_probs:
    outputline = f'{win_prob:.3f}; '
    for rank in relevant_ranks:
        outputline += f'{expected_games_with_tier_protection(win_prob, rank, 1):.3f}; '
    print(outputline)

# Second, output the Limited results as a plot
x_axis = np.arange(0.48, 0.64, 0.001)
y_axis = np.empty(161)
fig, ax = plt.subplots()
for rank in relevant_ranks:
    for i in range(0, 161):
        y_axis[i] = expected_games_with_tier_protection(0.48 + i / 1000, rank, 1)
    ax.plot(x_axis, y_axis, label=rank.title())
    ax.set(xlabel='Game win rate', ylabel='Expected number of games',
           title='Expected games to reach the next rank in Limited')
    ax.set_xticklabels(['{:.0%}'.format(x) for x in ax.get_xticks()])
    ax.grid()
    plt.legend()
fig.savefig("Expected_number_of_games_Limited.png")

# Third, give the impact of tier protection
for win_prob in [.5, .6]:
    number_games_exact = expected_games_without_tier_protection(win_prob, 'gold', 1)
    print(
        f'Under Preseason 2 Limited progression WITHOUT tier protection, the exact E[games] to go from gold '
        f'to the next rank in best-of-one with a {win_prob * 100:.1f}% winrate is {number_games_exact:.3f}.')

# Next, let's get the Preseason 2 results for Constructed.
STEP_PER_TIER = {
    'bronze': 6,
    'silver': 6,
    'gold': 6,
    'platinum': 6,
    'diamond': 6
}

for _rank in relevant_ranks:

    # First, output the Constructed results as semicolon separated values
    win_probs = [0.45, 0.5, 0.52, 0.54, 0.56, 0.6, 0.62, 0.64, 0.66, 0.68, 0.7, 0.75, 0.8]
    print(f'\nCONSTRUCTED win_prob in rank {_rank}; bo1; bo3; bo1 sim check; bo3 exact check')
    for win_prob in win_probs:
        outputline = f'{win_prob:.3f}; '
        outputline += f'{expected_games_with_tier_protection(win_prob, _rank, 1):.3f}; '
        outputline += f'{run_simulation(win_prob, _rank, 3):.3f}; '
        outputline += f'{run_simulation(win_prob, _rank, 1):.3f}; '
        outputline += f'{expected_games_with_tier_protection(win_prob, _rank, 3):.3f}'
        print(outputline)

    # Second, output the Constructed results as a plot
    x_axis = np.arange(0.48, 0.64, 0.01)
    y_axis = np.empty(17)
    fig, ax = plt.subplots()
    for i in range(0, 17):
        y_axis[i] = expected_games_with_tier_protection(0.48 + i / 100, _rank, 1)
    ax.plot(x_axis, y_axis, label='best-of-1')
    for i in range(0, 17):
        y_axis[i] = run_simulation(0.48 + i / 100, _rank, 3)
    ax.plot(x_axis, y_axis, label='best-of-3')

    ax.set(xlabel='Game win rate', ylabel='Expected number of games',
           title=f'Expected games from {_rank.title()} to the next rank in Constructed')
    ax.set_xticklabels(['{:.0%}'.format(x) for x in ax.get_xticks()])
    ax.grid()
    plt.legend()
    fig.savefig(f'Expected_number_of_games_Constructed_{_rank.title()}.png')
