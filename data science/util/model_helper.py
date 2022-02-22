

class Model:
    def __init__(self, name, version, shortname, model, pred_func, fit_func=None, post_process=None, calc_proba_func=None) -> None:
        self.name = name
        self.version = version
        self.shortname = shortname
        self.model = model
        self.__pred_func = pred_func
        self.__fit_func = fit_func
        self.__post_process = post_process
        self.__calc_proba_func = calc_proba_func
    
    def predict(self, x):
        y = self.__pred_func(self.model, x)
        y = self.__post_process(y) if self.__post_process else y
        y = self.__calc_proba_func(y) if self.__calc_proba_func else y
        
        return y

    def fit(self, x, y):
        if self.__fit_func is None:
            self.model.fit(x, y)

        return self.__fit_func(self.model, x, y)


class ModelLoader:
    def __init__(self, name, version, shortname, path, loader) -> None:
        self.name = name
        self.version = version
        self.shortname = shortname
        self.path = path
        self.loader = loader

    def load(self):
        return self.loader(self.path)
    
    def get_config(self):
        return {
            "name": self.name,
            "version": self.version,
            "shortname": self.shortname
        }