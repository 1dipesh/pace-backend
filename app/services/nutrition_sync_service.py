"""Canonical client records plus transactional projections for the existing read API.

All writers serialize on PaceUser. Once a namespace is initialized, legacy REST
writes are blocked: their schemas cannot preserve the frontend's extra fields.
"""
from datetime import datetime, timezone, date
from uuid import UUID, uuid5
from sqlalchemy import select, delete
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import PaceUser
from app.models.nutrition_sync import NutritionSyncRecord as Row
from app.models.nutrition import NutritionFood, NutritionEntry, NutritionGoal, NutritionSavedMeal, NutritionSavedMealItem

MODELS = {"foods": NutritionFood, "entries": NutritionEntry, "goals": NutritionGoal, "meals": NutritionSavedMeal}


def lock(db, uid):
    db.execute(select(PaceUser.id).where(PaceUser.id == uid).with_for_update()).scalar_one()


def legacy_write_guard(request: Request, db: Session = Depends(get_db), user: PaceUser = Depends(get_current_user)):
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        lock(db, user.id)
        if db.get(Row, (user.id, "meta", "initialized")):
            raise HTTPException(409, detail={"code": "nutrition_sync_required", "message": "Use /api/v1/sync/nutrition for this account. Legacy reads remain available."})


def record(row):
    return {"entity": row.entity, "id": row.client_id, "version": row.version, "data": row.data}


def mapped_id(uid, entity, client_id):
    # Legacy rows keep their IDs; frontend IDs map deterministically per owner.
    try:
        return UUID(client_id)
    except ValueError:
        return uuid5(uid, f"nutrition:{entity}:{client_id}")


def iso(value):
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def macros(row, suffix=""):
    return {k: float(getattr(row, f"{v}{suffix}")) for k, v in
            {"calories": "calories_kcal", "protein": "protein_g", "carbs": "carbs_g", "fat": "fat_g", "fiber": "fiber_g"}.items()
            if getattr(row, f"{v}{suffix}") is not None}


def bootstrap(db, uid):
    """Import existing REST records once, preserving IDs, ownership and snapshots."""
    if db.get(Row, (uid, "meta", "initialized")):
        return
    remapped = {}
    # Legacy REST allowed soft-deleting foods still used by diary entries or
    # templates. Preserve those references with a hidden archival food; retain
    # the original food's tombstone so it does not reappear in the library.
    deleted_foods = db.scalars(select(NutritionFood).where(NutritionFood.user_id == uid, NutritionFood.deleted_at.is_not(None))).all()
    for food in deleted_foods:
        used = db.scalar(select(NutritionEntry.id).where(NutritionEntry.user_id == uid, NutritionEntry.source_food_id == food.id, NutritionEntry.deleted_at.is_(None)).limit(1))
        used_item = db.scalar(select(NutritionSavedMealItem.id).where(NutritionSavedMealItem.user_id == uid, NutritionSavedMealItem.food_id == food.id, NutritionSavedMealItem.deleted_at.is_(None)).limit(1))
        if used or used_item:
            cid = f"legacy-food-{food.id}"
            data = dict(id=cid, name=food.name, category="other", basisAmount=float(food.basis_amount), basisUnit=food.basis_unit,
                        nutrition=macros(food), isStarter=False, isLibraryItem=False, createdAt=iso(food.created_at), updatedAt=iso(food.updated_at))
            if food.brand: data["brand"] = food.brand
            if food.preparation_state != "unspecified": data["preparation"] = food.preparation_state
            db.add(Row(user_id=uid, entity="foods", client_id=cid, version=1, data=data))
            project(db, uid, "foods", cid, data, 1)
            remapped[food.id] = cid
    for entity, model in MODELS.items():
        for obj in db.scalars(select(model).where(model.user_id == uid)).all():
            if entity == "foods" and obj.id in {mapped_id(uid, "foods", cid) for cid in remapped.values()}:
                continue
            cid = "default" if entity == "goals" else str(obj.id)
            base = {"id": cid, "createdAt": iso(obj.created_at), "updatedAt": iso(obj.client_updated_at or obj.updated_at)}
            if entity == "foods":
                data = dict(base, name=obj.name, category="other", basisAmount=float(obj.basis_amount), basisUnit=obj.basis_unit,
                            nutrition=macros(obj), isStarter=obj.source == "starter", isFavorite=obj.is_favorite)
                if obj.brand: data["brand"] = obj.brand
                if obj.preparation_state != "unspecified": data["preparation"] = obj.preparation_state
            elif entity == "entries":
                food_id = remapped.get(obj.source_food_id, str(obj.source_food_id)) if obj.source_food_id else f"legacy-snapshot-{obj.id}"
                data = dict(base, foodId=food_id, date=obj.logged_date.isoformat(), amount=float(obj.amount), unit=obj.unit,
                            foodName=obj.food_name_snapshot, nutrition=macros(obj, "_snapshot"), loggedAt=iso(obj.created_at))
                if obj.brand_snapshot: data["foodBrand"] = obj.brand_snapshot
                if obj.preparation_state_snapshot != "unspecified": data["foodPreparation"] = obj.preparation_state_snapshot
                if obj.source_food_id in remapped and not obj.deleted_at:
                    obj.source_food_id = mapped_id(uid, "foods", food_id)
                if not obj.source_food_id and not obj.deleted_at:
                    # A manually entered legacy snapshot needs a hidden food for
                    # the frontend's edit/repeat actions. Basis equals saved amount.
                    food = dict(id=food_id, name=obj.food_name_snapshot, category="other", basisAmount=float(obj.amount),
                                basisUnit=obj.unit, nutrition=data["nutrition"], isStarter=False, isLibraryItem=False,
                                createdAt=base["createdAt"], updatedAt=base["updatedAt"])
                    db.add(Row(user_id=uid, entity="foods", client_id=food_id, version=1, data=food))
                    project(db, uid, "foods", food_id, food, 1)
                    obj.source_food_id = mapped_id(uid, "foods", food_id)
            elif entity == "meals":
                items = db.scalars(select(NutritionSavedMealItem).where(NutritionSavedMealItem.user_id == uid,
                    NutritionSavedMealItem.meal_id == obj.id, NutritionSavedMealItem.deleted_at.is_(None))
                    .order_by(NutritionSavedMealItem.position)).all()
                data = dict(base, name=obj.name, items=[dict(foodId=remapped.get(i.food_id, str(i.food_id)), amount=float(i.amount)) for i in items])
            else:
                data = {"id": "default", "updatedAt": base["updatedAt"]}
                for field, column in {"calories": "target_calories_kcal", "protein": "target_protein_g", "carbs": "target_carbs_g", "fat": "target_fat_g", "fiber": "target_fiber_g"}.items():
                    if getattr(obj, column) is not None: data[field] = float(getattr(obj, column))
            db.add(Row(user_id=uid, entity=entity, client_id=cid, version=obj.version, data=None if obj.deleted_at else data))
            if entity == "meals" and not obj.deleted_at:
                for item in items:
                    if item.food_id in remapped: item.food_id = mapped_id(uid, "foods", remapped[item.food_id])
    db.add(Row(user_id=uid, entity="meta", client_id="initialized", version=1, data={}))
    db.flush()


def project(db, uid, entity, cid, data, version):
    model = MODELS[entity]
    oid = mapped_id(uid, entity, cid)
    if entity == "goals":
        obj = db.scalar(select(model).where(model.user_id == uid))
    else:
        obj = db.get(model, oid)
        if obj and obj.user_id != uid:
            raise HTTPException(422, detail={"code": "record_id_collision"})
    now = datetime.now(timezone.utc)
    # Optional frontend goals remain exact in the canonical record. The legacy
    # numeric schema can expose them only when all four required targets exist.
    incomplete_goals = entity == "goals" and data and any(data.get(k) is None for k in ("calories", "protein", "carbs", "fat"))
    if data is None or incomplete_goals:
        if obj:
            obj.deleted_at = now
            obj.version = version
        if entity == "meals" and obj:
            for item in db.scalars(select(NutritionSavedMealItem).where(NutritionSavedMealItem.meal_id == obj.id, NutritionSavedMealItem.user_id == uid)):
                item.deleted_at = now
        db.flush()
        return
    if not obj:
        obj = model(id=oid, user_id=uid)
        db.add(obj)
    obj.deleted_at = None
    obj.version = version
    obj.client_updated_at = datetime.fromisoformat(data["updatedAt"].replace("Z", "+00:00"))
    if "createdAt" in data: obj.created_at = datetime.fromisoformat(data["createdAt"].replace("Z", "+00:00"))
    if entity == "foods":
        obj.name, obj.brand = data["name"], data.get("brand")
        obj.basis_amount, obj.basis_unit = data["basisAmount"], data["basisUnit"]
        obj.preparation_state = data.get("preparation") if data.get("preparation") in ("raw", "cooked") else "unspecified"
        obj.source = "starter" if data["isStarter"] else "custom"
        obj.is_favorite = bool(data.get("isFavorite"))
    elif entity == "entries":
        obj.logged_date = date.fromisoformat(data["date"])
        obj.meal_type = getattr(obj, "meal_type", None) or "other"
        obj.amount, obj.unit = data["amount"], data["unit"]
        obj.source_food_id = mapped_id(uid, "foods", data["foodId"])
        obj.food_name_snapshot, obj.brand_snapshot = data["foodName"], data.get("foodBrand")
        obj.preparation_state_snapshot = data.get("foodPreparation") if data.get("foodPreparation") in ("raw", "cooked") else "unspecified"
    elif entity == "goals":
        for k, column in {"calories": "target_calories_kcal", "protein": "target_protein_g", "carbs": "target_carbs_g", "fat": "target_fat_g", "fiber": "target_fiber_g"}.items():
            setattr(obj, column, data.get(k))
    else:
        obj.name = data["name"]
    if entity in ("foods", "entries"):
        for k, column in {"calories": "calories_kcal", "protein": "protein_g", "carbs": "carbs_g", "fat": "fat_g", "fiber": "fiber_g"}.items():
            setattr(obj, column + ("_snapshot" if entity == "entries" else ""), data["nutrition"].get(k))
    db.flush()
    if entity == "meals":
        db.execute(delete(NutritionSavedMealItem).where(NutritionSavedMealItem.user_id == uid, NutritionSavedMealItem.meal_id == obj.id))
        for i, item in enumerate(data["items"]):
            food = db.get(NutritionFood, mapped_id(uid, "foods", item["foodId"]))
            db.add(NutritionSavedMealItem(user_id=uid, meal_id=obj.id, food_id=food.id, amount=item["amount"], unit=food.basis_unit, position=i))
        db.flush()
