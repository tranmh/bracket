import random
from decimal import Decimal

import pytest

from bracket.logic.scheduling import ladder_teams
from bracket.logic.scheduling.ladder_teams import get_possible_upcoming_matches_for_swiss
from bracket.models.db.match import (
    Match,
    MatchFilter,
    MatchWithDetailsDefinitive,
    SuggestedMatch,
    get_match_hash,
)
from bracket.models.db.stage_item_inputs import (
    StageItemInput,
    StageItemInputFinal,
)
from bracket.models.db.team import Team
from bracket.models.db.util import RoundWithMatches
from bracket.utils.dummy_records import (
    DUMMY_MATCH1,
    DUMMY_TEAM1,
)
from bracket.utils.id_types import (
    MatchId,
    RoundId,
    StageItemId,
    StageItemInputId,
    TeamId,
    TournamentId,
)
from tests.integration_tests.mocks import MOCK_NOW

MATCH_FILTER = MatchFilter(elo_diff_threshold=50, iterations=100, limit=20, only_recommended=False)


def get_match(
    match: Match, stage_item_input1: StageItemInputFinal, stage_item_input2: StageItemInputFinal
) -> MatchWithDetailsDefinitive:
    return MatchWithDetailsDefinitive(
        **match.model_copy(
            update={
                "stage_item_input1_id": stage_item_input1.id,
                "stage_item_input2_id": stage_item_input2.id,
            }
        ).model_dump(),
        stage_item_input1=stage_item_input1,
        stage_item_input2=stage_item_input2,
        court=None,
    )


def test_constraints() -> None:
    stage_item_input_dummy = StageItemInputFinal(
        id=StageItemInputId(-1),
        tournament_id=TournamentId(-1),
        team_id=TeamId(-1),
        slot=0,
        points=Decimal("2.0"),
        wins=1,
        draws=0,
        losses=0,
        team=Team(**DUMMY_TEAM1.model_dump(), id=TeamId(-1)),
    )
    input1 = stage_item_input_dummy.model_copy(update={"id": -1, "points": Decimal("1125.0")})
    input2 = stage_item_input_dummy.model_copy(update={"id": -2, "points": Decimal("1175.0")})
    input3 = stage_item_input_dummy.model_copy(update={"id": -3, "points": Decimal("1200.0")})
    input4 = stage_item_input_dummy.model_copy(update={"id": -4, "points": Decimal("1250.0")})

    rounds = [
        RoundWithMatches(
            id=RoundId(-1),
            matches=[
                get_match(
                    Match.model_validate(DUMMY_MATCH1.model_dump() | {"id": MatchId(-1)}),
                    input1,
                    input2,
                )
            ],
            is_draft=False,
            stage_item_id=StageItemId(-1),
            name="R1",
            created=MOCK_NOW,
        ),
        RoundWithMatches(
            id=RoundId(-2),
            matches=[],
            is_draft=True,
            stage_item_id=StageItemId(-1),
            name="R2",
            created=MOCK_NOW,
        ),
    ]
    inputs: list[StageItemInput] = [input1, input2, input3, input4]
    result = get_possible_upcoming_matches_for_swiss(MATCH_FILTER, rounds, inputs)

    # Team 3 and 4 haven't played yet, so any suggested match with one or more of those teams
    # is recommended.
    assert result == [
        SuggestedMatch(
            stage_item_input1=input4,
            stage_item_input2=input3,
            elo_diff=Decimal("50.0"),
            swiss_diff=Decimal("50.0"),
            is_recommended=True,
            times_played_sum=0,
            player_behind_schedule_count=0,
        ),
        SuggestedMatch(
            stage_item_input1=input3,
            stage_item_input2=input2,
            elo_diff=Decimal("25.0"),
            swiss_diff=Decimal("25.0"),
            is_recommended=False,
            times_played_sum=1,
            player_behind_schedule_count=0,
        ),
    ]


def test_dedupe_of_suggestions_scales_linearly(monkeypatch: pytest.MonkeyPatch) -> None:
    comparisons = 0

    class CountingHash(str):
        __hash__ = str.__hash__

        def __eq__(self, other: object) -> bool:
            nonlocal comparisons
            comparisons += 1
            return str.__eq__(self, other)

    monkeypatch.setattr(
        ladder_teams,
        "get_match_hash",
        lambda id1, id2: CountingHash(get_match_hash(id1, id2)),
    )

    stage_item_input_dummy = StageItemInputFinal(
        id=StageItemInputId(-1),
        tournament_id=TournamentId(-1),
        team_id=TeamId(-1),
        slot=0,
        points=Decimal("1000.0"),
        wins=0,
        draws=0,
        losses=0,
        team=Team(**DUMMY_TEAM1.model_dump(), id=TeamId(-1)),
    )
    inputs: list[StageItemInput] = [
        stage_item_input_dummy.model_copy(update={"id": StageItemInputId(i)})
        for i in range(1, 1001)
    ]

    def count_comparisons(iterations: int) -> int:
        nonlocal comparisons
        comparisons = 0
        random.seed(0)
        match_filter = MatchFilter(
            elo_diff_threshold=1_000_000, iterations=iterations, limit=20, only_recommended=False
        )
        get_possible_upcoming_matches_for_swiss(match_filter, [], inputs)
        return comparisons

    comparisons_n = count_comparisons(1_000)
    comparisons_2n = count_comparisons(2_000)

    # Doubling the iterations should roughly double the dedupe work, not quadruple it.
    assert comparisons_2n <= 3 * comparisons_n + 2 * 2_000
