from fastapi import APIRouter
from app.core.visual_mapper import VisualMapper

router = APIRouter()


@router.get("/api/styles")
def get_styles():
    # 默认加载主映射和风格映射文件，可根据实际路径调整
    mapper = VisualMapper(
        mappings_filename="mappings/mappings_main.json",
        styles_filename="mappings/mappings_styles.json",
    )
    return {"styles": list(mapper.styles.keys())}
