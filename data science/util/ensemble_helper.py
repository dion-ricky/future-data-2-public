from typing import List

import numpy as np

from .model_helper import Model

class ModelConcatenate:
    def __init__(self, models: List[Model]) -> None:
        self.__models = models
    
    def predict(self, x):
        predicted = []

        for model in self.__models:
            predicted.append(model.predict(x))
        
        return np.array(predicted)
    
    def orders(self):
        model_sn = []

        for model in self.__models:
            model_sn.append(model.shortname)

        return "[ {m} ]".format(m=', '.join(model_sn))

class StackingEnsemble:
    def __init__(self, concat: ModelConcatenate, meta_classifier: Model) -> None:
        self.concat = concat
        self.meta_classifier = meta_classifier
    
    def fit(self, x, y):
        x_hat = self.concat.predict(x)
        x_hat = np.transpose(x_hat)

        return self.meta_classifier.fit(x_hat, y)

    def predict(self, x):
        x_hat = self.concat.predict(x)
        x_hat = np.transpose(x_hat)
        
        return self.meta_classifier.predict(x_hat)

class VotingEnsemble:
    def __init__(self, concat: ModelConcatenate) -> None:
        self.concat = concat
    
    def predict(self, x):
        y = self.concat.predict(x)
        y = np.sum(y, axis=0)

        return np.argmax(y, axis=1)
    
    def predict_support(self, x):
        y = self.concat.predict(x)
        y = np.sum(y, axis=0)

        return y