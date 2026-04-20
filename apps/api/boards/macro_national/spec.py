from __future__ import annotations

from boards.macro_national.router import router
from boards.macro_national.schemas import EXPECTED_FILES
from boards.registry import BoardSpec

BOARD_SPEC = BoardSpec(
    slug="macro-national",
    title="Macro National",
    description=(
        "Tableau de bord hebdomadaire de suivi RSU: inscriptions, "
        "traitement FMS, flux ASD, ménages bloqués."
    ),
    expected_files=EXPECTED_FILES,
    router=router,
)
