from __future__ import annotations

from boards.programmes_sociaux_rescoring.router import router
from boards.registry import BoardSpec

BOARD_SPEC = BoardSpec(
    slug="programmes-sociaux-rescoring",
    title="Programmes sociaux / Rescoring",
    description=(
        "Suivi des programmes sociaux depuis la source CSV RSU: éligibilité, "
        "entrées/sorties de seuil, volatilité et lecture territoriale."
    ),
    expected_files=[],
    router=router,
)
