import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from configurar_numero import find_phone, save_env


class ConfigurarNumero(unittest.TestCase):
    def test_reemplaza_configuracion_sin_perder_otros_ajustes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / ".env"
            path.write_text("PORT=8765\nWA_PHONE_ID=1\nWA_PHONE_ID=2\n", encoding="utf-8")
            save_env(path, {"WA_PHONE_ID": "3"})
            self.assertEqual(path.read_text().splitlines(), ["PORT=8765", "WA_PHONE_ID=3"])

    def test_busca_en_segunda_pagina(self):
        phone = {"id": "42", "display_phone_number": "+591 00000000"}
        pages = [{"data": [], "paging": {"next": "url", "cursors": {"after": "abc"}}}, {"data": [phone]}]
        with patch("configurar_numero.graph", side_effect=pages):
            self.assertEqual(find_phone("v27.0", "82", "42", "token"), phone)

    def test_rechaza_numero_de_otra_cuenta(self):
        with patch("configurar_numero.graph", return_value={"data": []}), self.assertRaises(ValueError):
            find_phone("v27.0", "82", "42", "token")
