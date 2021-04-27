# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/distributed.models.ipynb (unless otherwise specified).

__all__ = ['LGBMForecast', 'XGBForecast']

# Cell
from typing import Callable, Dict, List, Optional, Tuple

import dask.dataframe as dd
import lightgbm as lgb
import xgboost as xgb
from dask.distributed import Client, default_client, Future

from ..core import predictions_flow

# Internal Cell
class BaseDistributedModel:

    def __init__(self, model, client: Optional[Client] = None):
        self.model = model
        self.client = client or default_client()

    def fit(self, X: dd.DataFrame, y: dd.Series, **kwargs):
        self.model.fit(X, y, **kwargs)
        return self

    @property
    def model_(self):
        raise NotImplementedError

    def predict(self,
                series: List[Future],
                horizon: int,
                divisions: Optional[Tuple] = None,
                predict_fn: Optional[Callable] = predictions_flow) -> dd.DataFrame:
        model_future = self.client.scatter(self.model_, broadcast=True)
        predictions_futures = self.client.map(predict_fn,
                                              series,
                                              model=model_future,
                                              horizon=horizon)
        meta = self.client.submit(lambda x: x.head(), predictions_futures[0]).result()
        return dd.from_delayed(predictions_futures, meta=meta, divisions=divisions)

    def __repr__(self) -> str:
        return self.model.__repr__()

# Cell
class LGBMForecast(BaseDistributedModel):

    def __init__(self, params: Dict = {}, client: Optional[Client] = None):
        super().__init__(lgb.DaskLGBMRegressor(**params), client)

    @property
    def model_(self):
        return self.model.booster_

# Cell
class XGBForecast(BaseDistributedModel):

    def __init__(self, params: Dict = {}, client: Optional[Client] = None):
        super().__init__(xgb.dask.DaskXGBRegressor(**params), client)

    @property
    def model_(self):
        return self.model.get_booster()