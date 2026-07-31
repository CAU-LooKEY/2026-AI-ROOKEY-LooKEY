import os
import unittest

from app.core.settings import get_settings
from app.services.k_exaone import KExaoneClient


@unittest.skipUnless(
    os.getenv("RUN_K_EXAONE_SMOKE") == "1",
    "Set RUN_K_EXAONE_SMOKE=1 to call the real K-EXAONE API.",
)
class KExaoneSmokeTest(unittest.IsolatedAsyncioTestCase):
    async def test_real_api_returns_a_valid_circuit_contract(self):
        settings = get_settings()
        self.assertTrue(
            settings.is_configured,
            "K_EXAONE_API_KEY and K_EXAONE_ENDPOINT_ID are required.",
        )

        result = await KExaoneClient(settings).generate_circuit(
            "LED를 1초 간격으로 켰다 껐다 반복하는 회로를 만들어줘"
        )

        self.assertTrue(result.circuit.parts)
        self.assertTrue(result.circuit.connections)
        self.assertIsNotNone(result.assembly_plan)


if __name__ == "__main__":
    unittest.main()
