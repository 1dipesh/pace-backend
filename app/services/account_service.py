from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Session

from app.models.alcohol import AlcoholBreak, AlcoholDrink, AlcoholFavorite, AlcoholSession, AlcoholWaterEntry
from app.models.alcohol_sync import AlcoholSyncRecord
from app.models.endurance import CardioActivity, HybridSegment, HybridSession
from app.models.nutrition import NutritionEntry, NutritionFood, NutritionGoal, NutritionSavedMeal, NutritionSavedMealItem
from app.models.nutrition_sync import NutritionSyncRecord
from app.models.profile import PaceProfile
from app.models.sync import SyncReceipt
from app.models.training import (
    TrainingExercise,
    TrainingSession,
    TrainingSessionExercise,
    TrainingSet,
    TrainingSettings,
    TrainingTemplate,
    TrainingTemplateExercise,
    TrainingTemplateSet,
)
from app.models.training_sync import TrainingSyncRecord
from app.models.user import PaceUser


EXPORT_MODELS = (
    PaceProfile,
    NutritionGoal,
    NutritionFood,
    NutritionEntry,
    NutritionSavedMeal,
    NutritionSavedMealItem,
    TrainingExercise,
    TrainingSettings,
    TrainingTemplate,
    TrainingTemplateExercise,
    TrainingTemplateSet,
    TrainingSession,
    TrainingSessionExercise,
    TrainingSet,
    CardioActivity,
    HybridSession,
    HybridSegment,
    AlcoholSession,
    AlcoholDrink,
    AlcoholWaterEntry,
    AlcoholBreak,
    AlcoholFavorite,
    SyncReceipt,
    NutritionSyncRecord,
    TrainingSyncRecord,
    AlcoholSyncRecord,
)

# Children precede parents so deletion works with both PostgreSQL and SQLite,
# including the intentional RESTRICT foreign keys used by saved records.
DELETE_MODELS = (
    TrainingSet,
    TrainingSessionExercise,
    TrainingTemplateSet,
    TrainingTemplateExercise,
    HybridSegment,
    AlcoholBreak,
    AlcoholDrink,
    AlcoholWaterEntry,
    NutritionSavedMealItem,
    TrainingSession,
    TrainingTemplate,
    HybridSession,
    CardioActivity,
    AlcoholSession,
    AlcoholFavorite,
    NutritionEntry,
    NutritionSavedMeal,
    NutritionFood,
    NutritionGoal,
    TrainingSettings,
    TrainingExercise,
    PaceProfile,
    SyncReceipt,
    NutritionSyncRecord,
    TrainingSyncRecord,
    AlcoholSyncRecord,
)


def _json_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    return value


def _row(row) -> dict:
    return {
        column.key: _json_value(getattr(row, column.key))
        for column in inspect(row).mapper.column_attrs
    }


def export_account(db: Session, user: PaceUser) -> dict:
    data = {}
    for model in EXPORT_MODELS:
        rows = db.scalars(select(model).where(model.user_id == user.id)).all()
        data[model.__tablename__] = [_row(row) for row in rows]
    return {
        "format": "pace-account-export",
        "format_version": 1,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "account": {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        },
        "data": data,
    }


def delete_account(db: Session, user: PaceUser) -> None:
    # Lock the account so a concurrent sync request cannot recreate rows midway.
    db.execute(select(PaceUser.id).where(PaceUser.id == user.id).with_for_update()).scalar_one()
    try:
        for model in DELETE_MODELS:
            db.execute(delete(model).where(model.user_id == user.id))
        db.delete(user)
        db.commit()
    except Exception:
        db.rollback()
        raise
