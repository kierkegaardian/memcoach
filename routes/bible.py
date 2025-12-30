from fastapi import APIRouter, Depends, HTTPException, Query

from utils.auth import require_parent_session
from utils.bible import get_passage

router = APIRouter(dependencies=[Depends(require_parent_session)])


@router.get("/bible/passage")
async def bible_passage(
    book: str = Query(..., min_length=1),
    chapter: int = Query(..., ge=1),
    start_verse: int = Query(..., ge=1),
    end_verse: int = Query(..., ge=1),
    translation: str = Query("KJV"),
):
    if start_verse > end_verse:
        raise HTTPException(status_code=400, detail="Start verse must be <= end verse")
    passage = get_passage(
        translation=translation,
        book=book,
        chapter=chapter,
        start_verse=start_verse,
        end_verse=end_verse,
        include_verses=True,
    )
    if not passage.get("verses"):
        raise HTTPException(status_code=404, detail="Passage not found")
    passage.update(
        {
            "book": book,
            "chapter": chapter,
            "start_verse": start_verse,
            "end_verse": end_verse,
        }
    )
    return passage
