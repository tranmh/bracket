from collections import Counter
from itertools import combinations
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bracket.logic.scheduling import round_robin
from bracket.logic.scheduling.round_robin import (
    build_round_robin_stage_item,
    get_number_of_rounds_to_create_round_robin,
    get_round_robin_combinations,
)
from bracket.models.db.match import MatchCreateBody
from bracket.models.db.stage_item import StageType
from bracket.models.db.stage_item_inputs import StageItemInputFinal
from bracket.models.db.team import Team
from bracket.models.db.util import RoundWithMatches, StageItemWithRounds
from bracket.utils.dummy_records import DUMMY_MOCK_TIME
from bracket.utils.id_types import (
    RoundId,
    StageId,
    StageItemId,
    StageItemInputId,
    TeamId,
    TournamentId,
)


@pytest.mark.parametrize("team_count", [0, -1, -5])
def test_round_robin_combinations_no_teams(team_count: int) -> None:
    assert get_round_robin_combinations(team_count) == []


def test_round_robin_combinations_one_team_gets_only_a_bye() -> None:
    # Phantom team index 1 stands for the bye.
    assert get_round_robin_combinations(1) == [[(0, 1)]]


def test_round_robin_combinations_two_teams() -> None:
    assert get_round_robin_combinations(2) == [[(0, 1)]]


def test_round_robin_combinations_three_teams() -> None:
    result = get_round_robin_combinations(3)
    assert len(result) == 3
    assert all(len(round_) == 2 for round_ in result)
    # Every real team has exactly one bye (pairing with phantom team 3).
    byes = Counter(team for round_ in result for pair in round_ if 3 in pair for team in pair)
    assert byes == {3: 3, 0: 1, 1: 1, 2: 1}


@pytest.mark.parametrize("team_count", list(range(2, 17)))
def test_round_robin_combinations_properties(team_count: int) -> None:
    result = get_round_robin_combinations(team_count)
    is_odd = team_count % 2 == 1
    slots = team_count + 1 if is_odd else team_count

    # rr-1: n-1 rounds for even n, n rounds for odd n; each round has slots/2 pairings
    assert len(result) == (team_count if is_odd else team_count - 1)
    for round_ in result:
        assert len(round_) == slots // 2
        teams_in_round = [team for pair in round_ for team in pair]
        # No team plays twice in a round and every slot is used once.
        assert sorted(teams_in_round) == list(range(slots))

    # Every pair occurs exactly once (including the bye pairings for odd counts).
    pairs = Counter(frozenset(pair) for round_ in result for pair in round_)
    assert set(pairs.keys()) == {frozenset(p) for p in combinations(range(slots), 2)}
    assert all(count == 1 for count in pairs.values())

    if is_odd:
        bye_per_team = Counter(
            team for round_ in result for pair in round_ if team_count in pair for team in pair
        )
        for team in range(team_count):
            assert bye_per_team[team] == 1


@pytest.mark.parametrize(
    ("team_count", "expected"),
    [(-3, 0), (0, 0), (1, 1), (2, 1), (3, 3), (4, 3), (5, 5), (8, 7), (63, 63), (64, 63)],
)
def test_number_of_rounds_to_create_round_robin(team_count: int, expected: int) -> None:
    assert get_number_of_rounds_to_create_round_robin(team_count) == expected


@pytest.mark.parametrize("team_count", list(range(1, 17)))
def test_number_of_rounds_matches_combinations(team_count: int) -> None:
    assert get_number_of_rounds_to_create_round_robin(team_count) == len(
        get_round_robin_combinations(team_count)
    )


def _make_input(index: int, tournament_id: TournamentId) -> StageItemInputFinal:
    team_id = TeamId(100 + index)
    return StageItemInputFinal(
        id=StageItemInputId(10 + index),
        team_id=team_id,
        slot=index + 1,
        tournament_id=tournament_id,
        team=Team(
            id=team_id,
            name=f"Team {index}",
            created=DUMMY_MOCK_TIME,
            tournament_id=tournament_id,
            active=True,
        ),
    )


def _make_stage_item(team_count: int, rounds_count: int) -> StageItemWithRounds:
    tournament_id = TournamentId(1)
    return StageItemWithRounds(
        id=StageItemId(1),
        stage_id=StageId(1),
        name="RR",
        created=DUMMY_MOCK_TIME,
        type=StageType.ROUND_ROBIN,
        team_count=team_count,
        rounds=[
            RoundWithMatches(
                id=RoundId(1000 + i),
                stage_item_id=StageItemId(1),
                created=DUMMY_MOCK_TIME,
                is_draft=False,
                name=f"Round {i}",
                matches=[],
            )
            for i in range(rounds_count)
        ],
        inputs=[_make_input(i, tournament_id) for i in range(team_count)],
    )


async def test_build_round_robin_stage_item_skips_bye_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stage_item = _make_stage_item(team_count=3, rounds_count=3)
    tournament = SimpleNamespace(duration_minutes=12, margin_minutes=3)
    get_tournament = AsyncMock(return_value=tournament)
    create_match = AsyncMock()
    monkeypatch.setattr(round_robin, "sql_get_tournament", get_tournament)
    monkeypatch.setattr(round_robin, "sql_create_match", create_match)

    await build_round_robin_stage_item(TournamentId(1), stage_item)

    get_tournament.assert_awaited_once_with(TournamentId(1))
    created: list[MatchCreateBody] = [call.args[0] for call in create_match.await_args_list]
    # 3 teams -> 3 rounds of 2 pairings, one of which is a bye each round -> 3 real matches
    assert len(created) == 3
    input_ids = [inp.id for inp in stage_item.inputs]
    pairs = {frozenset({m.stage_item_input1_id, m.stage_item_input2_id}) for m in created}
    assert pairs == {frozenset(p) for p in combinations(input_ids, 2)}
    # One match per round
    assert sorted(m.round_id for m in created) == [1000, 1001, 1002]
    for match in created:
        assert match.court_id is None
        assert match.duration_minutes == 12
        assert match.margin_minutes == 3
        assert match.custom_duration_minutes is None
        assert match.custom_margin_minutes is None
        assert match.stage_item_input1_winner_from_match_id is None
        assert match.stage_item_input2_winner_from_match_id is None


async def test_build_round_robin_stage_item_even_team_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stage_item = _make_stage_item(team_count=4, rounds_count=3)
    create_match = AsyncMock()
    monkeypatch.setattr(
        round_robin,
        "sql_get_tournament",
        AsyncMock(return_value=SimpleNamespace(duration_minutes=20, margin_minutes=5)),
    )
    monkeypatch.setattr(round_robin, "sql_create_match", create_match)

    await build_round_robin_stage_item(TournamentId(1), stage_item)

    created: list[MatchCreateBody] = [call.args[0] for call in create_match.await_args_list]
    assert len(created) == 6
    per_round = Counter(m.round_id for m in created)
    assert per_round == {1000: 2, 1001: 2, 1002: 2}
    for round_id in per_round:
        inputs_in_round = [
            i
            for m in created
            if m.round_id == round_id
            for i in (m.stage_item_input1_id, m.stage_item_input2_id)
        ]
        assert len(set(inputs_in_round)) == 4
