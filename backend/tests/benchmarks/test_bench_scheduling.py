from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from bracket.logic.planning.conflicts import get_conflicting_matches
from bracket.logic.scheduling.elimination import (
    determine_matches_first_round,
    get_number_of_rounds_to_create_single_elimination,
)
from bracket.logic.scheduling.round_robin import (
    get_number_of_rounds_to_create_round_robin,
    get_round_robin_combinations,
)
from bracket.models.db.match import MatchWithDetailsDefinitive

BASE_TIME = datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc)


def _build_stages(match_count: int) -> list[SimpleNamespace]:
    # Matches share inputs in a sliding window and partly overlap in time, so both
    # the pair scan and the conflict-marking branch are exercised.
    matches = []
    for i in range(match_count):
        matches.append(
            MatchWithDetailsDefinitive.model_construct(
                id=i + 1,
                created=BASE_TIME,
                start_time=BASE_TIME + timedelta(minutes=5 * (i // 4)),
                duration_minutes=10,
                margin_minutes=5,
                round_id=1,
                stage_item_input1_score=0,
                stage_item_input2_score=0,
                stage_item_input1_conflict=False,
                stage_item_input2_conflict=False,
                stage_item_input1_id=(i % 50) + 1,
                stage_item_input2_id=((i + 7) % 50) + 1,
                stage_item_input1=None,
                stage_item_input2=None,
                court=None,
            )
        )
    round_ = SimpleNamespace(matches=matches)
    stage_item = SimpleNamespace(rounds=[round_])
    return [SimpleNamespace(stage_items=[stage_item])]


@pytest.mark.parametrize("match_count", [100, 400, 1600])
def test_bench_get_conflicting_matches(benchmark, match_count: int) -> None:
    stages = _build_stages(match_count)
    result = benchmark(get_conflicting_matches, stages)
    assert len(result[0]) + len(result[1]) == match_count


@pytest.mark.parametrize("team_count", [8, 64, 512])
def test_bench_get_round_robin_combinations(benchmark, team_count: int) -> None:
    result = benchmark(get_round_robin_combinations, team_count)
    assert len(result) == get_number_of_rounds_to_create_round_robin(team_count)


@pytest.mark.parametrize("team_count", [7, 63, 511])
def test_bench_get_round_robin_combinations_odd(benchmark, team_count: int) -> None:
    result = benchmark(get_round_robin_combinations, team_count)
    assert len(result) == team_count


def test_bench_get_number_of_rounds_to_create_round_robin(benchmark) -> None:
    counts = list(range(0, 1000))

    def run() -> int:
        return sum(get_number_of_rounds_to_create_round_robin(c) for c in counts)

    result = benchmark(run)
    assert result > 0


@pytest.mark.parametrize("team_count", [2, 8, 32])
def test_bench_determine_matches_first_round(benchmark, team_count: int) -> None:
    round_ = SimpleNamespace(id=1)
    stage_item = SimpleNamespace(inputs=[SimpleNamespace(id=i + 1) for i in range(team_count)])
    tournament = SimpleNamespace(duration_minutes=10, margin_minutes=5)
    result = benchmark(determine_matches_first_round, round_, stage_item, tournament)
    assert len(result) == team_count // 2


@pytest.mark.parametrize("team_count", [2, 16, 32])
def test_bench_get_number_of_rounds_to_create_single_elimination(
    benchmark, team_count: int
) -> None:
    result = benchmark(get_number_of_rounds_to_create_single_elimination, team_count)
    assert result >= 1
