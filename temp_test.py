# from pydantic import BaseModel
# from typing import Optional

# class T(BaseModel):
#     x: Optional[int] = None
#     y: Optional[int] = None

# class Outer(BaseModel):
#     t: 'T'

# Outer.model_rebuild()

# o = Outer(t={})
# print('exclude_unset', o.model_dump(exclude_unset=True))
# print('default', o.model_dump())

