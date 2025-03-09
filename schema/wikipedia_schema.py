from pydantic import BaseModel
from typing import Optional

class SearchModel(BaseModel):
    search: str