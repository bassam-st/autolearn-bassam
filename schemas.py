from pydantic import BaseModel

class DocIn(BaseModel):
    url: str
    title: str
    text: str
    source: str = "web"
    lang: str = "ar"
