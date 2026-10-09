from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from .dependencies import CurrentUser, DbSession
from .models import PostalMunicipality, PostalSettlement, PostalState, UserRole

router = APIRouter(prefix='/api/postal', tags=['Direcciones del taller'])


def authorize(user) -> None:
    if user.role not in (UserRole.ADMINISTRADOR, UserRole.RECEPCIONISTA):
        raise HTTPException(403, 'Solo administradores y recepcionistas pueden gestionar talleres.')


@router.get('/states')
def states(user: CurrentUser, db: DbSession) -> list[str]:
    authorize(user)
    values = list(db.scalars(select(PostalState.name).order_by(PostalState.name)))
    if not values:
        raise HTTPException(503, 'El catálogo postal todavía no está cargado.')
    return values


@router.get('/municipalities')
def municipalities(user: CurrentUser, db: DbSession, state: str = Query(min_length=1, max_length=100)) -> list[str]:
    authorize(user)
    return list(db.scalars(select(PostalMunicipality.name).join(PostalMunicipality.state_record)
                           .where(PostalState.name == state).order_by(PostalMunicipality.name)))


@router.get('/settlements')
def settlements(user: CurrentUser, db: DbSession,
                postal_code: str | None = Query(None, pattern=r'^\d{5}$'),
                state: str | None = Query(None, max_length=100),
                municipality: str | None = Query(None, max_length=100)) -> list[dict]:
    authorize(user)
    query = select(PostalSettlement).join(PostalSettlement.municipality_record).join(PostalMunicipality.state_record)
    if postal_code:
        query = query.where(PostalSettlement.postal_code == postal_code)
    elif state and municipality:
        query = query.where(PostalState.name == state, PostalMunicipality.name == municipality)
    else:
        raise HTTPException(422, 'Indica el código postal o el estado y municipio.')
    rows = db.scalars(query.order_by(PostalSettlement.neighborhood, PostalSettlement.postal_code)).all()
    if not rows:
        raise HTTPException(404, 'No se encontraron asentamientos para esta dirección.')
    return [dict(id=row.id, postal_code=row.postal_code, state=row.municipality_record.state_record.name,
                 municipality=row.municipality_record.name, neighborhood=row.neighborhood) for row in rows]
