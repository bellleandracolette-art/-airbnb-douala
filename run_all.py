
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.scraper.scraper    import run as run_scraper
from src.pipeline.processor import run as run_pipeline

if __name__ == "__main__":
    print("ETAPE 1 - Collecte des donnees")
    run_scraper()
    print("ETAPE 2 - Pipeline de traitement")
    run_pipeline()
    print("ETAPE 3 - Dashboard")
    print("Lance : python src/dashboard/app.py")
    print("Puis ouvre : http://localhost:8050")
