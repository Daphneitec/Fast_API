from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI

from abacus.schemas import AddOut, HealthOut, NumberIn, ResetOut, SumOut
from abacus.settings import Settings, get_settings
from abacus.store import SumStore, as_json_number, build_store

_store: SumStore | None = None


def get_store() -> SumStore:
    if _store is None:
        raise RuntimeError("Store is not initialized")
    return _store


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _store
    settings = get_settings()
    _store = build_store(settings)
    await _store.connect()
    app.state.store = _store
    app.state.settings = settings
    try:
        yield
    finally:
        await _store.close()
        _store = None


app = FastAPI(
    title="Abacus",
    description="Running-sum service with a shared strongly consistent store.",
    lifespan=lifespan,
)

StoreDep = Annotated[SumStore, Depends(get_store)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


@app.get("/health", response_model=HealthOut)
async def health(settings: SettingsDep) -> HealthOut:
    return HealthOut(status="ok", node=settings.node_name, store=settings.store)


@app.post("/abacus/number", response_model=AddOut)
async def add_number(
    payload: NumberIn, store: StoreDep, settings: SettingsDep
) -> AddOut:
    new_sum = await store.add(float(payload.number))
    return AddOut(
        added=as_json_number(payload.number),
        sum=as_json_number(new_sum),
        node=settings.node_name,
    )


@app.get("/abacus/sum", response_model=SumOut)
async def get_sum(store: StoreDep) -> SumOut:
    return SumOut(sum=as_json_number(await store.get()))


@app.delete("/abacus/sum", response_model=ResetOut)
async def reset_sum(store: StoreDep, settings: SettingsDep) -> ResetOut:
    await store.reset()
    return ResetOut(sum=0, node=settings.node_name)
