import re

with open("app/api/v1/notifications.py", "r") as f:
    content = f.read()

delete_endpoint = """
@router.delete("/device-token", response_model=APIResponse)
async def delete_device_token(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    from app.dependencies.auth import get_db_user_from_auth
    user = await get_db_user_from_auth(db, current_user)
    
    stmt = select(UserDeviceToken).where(UserDeviceToken.token == token, UserDeviceToken.user_id == user.id)
    res = await db.execute(stmt)
    token_record = res.scalars().first()
    
    if token_record:
        token_record.is_active = False
        await db.commit()
        
    return APIResponse(success=True, message="Device token deactivated.")
"""

content += delete_endpoint

with open("app/api/v1/notifications.py", "w") as f:
    f.write(content)
