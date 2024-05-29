import os
import dotenv

dotenv.load_dotenv()

BC_BANDNAME = os.environ.get("BC_BANDNAME")
BC_ALBUMNAME = os.environ.get("BC_ALBUMNAME")
BC_TRACKNAME = os.environ.get("BC_TRACKNAME")
