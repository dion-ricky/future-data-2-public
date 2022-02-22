import re

from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory

from nltk.tokenize import RegexpTokenizer

from .new_stopwords import NEW_SW
from .indonesian_formalization import ID_FORMALIZATION_DICT


class StopWordRemoverFactory(StopWordRemoverFactory):
    def get_stop_words(self):
        new_sw = NEW_SW

        new_sw.extend(super().get_stop_words())

        return list(set(new_sw))


class Stemming:
    def __init__(self):
        factory = StemmerFactory()

        self.stemmer = factory.create_stemmer()

    def stem(self, value):
        return self.stemmer.stem(value)

class Formalization:
    def __init__(self):
        self.id_formalization = ID_FORMALIZATION_DICT
    
    def convert_all(self, l):
        return [self.convert_all(x) if isinstance(x, list) else self.convert(x) for x in l]

    def convert(self, x):
        d = self.id_formalization
        return d.get(x, x)

class TextTokenizer:
    def __init__(self):
        self.texts = []
        self.tokenizer = RegexpTokenizer(r'\w+')
    
    def tokenize_all(self, docs):
        texts = []

        for doc in docs:
            tokens = self.tokenize(doc)
            texts.append(tokens)
        
        return texts
    
    def tokenize(self, doc):
        return self.tokenizer.tokenize(doc)


class LDATextPreprocess:
    def __init__(self, sw_remover, stemmer, tokenizer, formalizer):
        self.sw_remover = sw_remover if sw_remover else lambda x: x
        self.stemmer = stemmer if stemmer else lambda x: x
        self.tokenizer = tokenizer if tokenizer else lambda x: x
        self.formalizer = formalizer if formalizer else lambda x: x
    
    def preprocess(self, docs):
        _docs = []

        for doc in docs:
            text = self._preprocess(doc)
            text = self.tokenizer(text)
            text = self.formalizer(text)
            _docs.append(text)

        return _docs
    
    def _preprocess(self, value):
        value = value.lower()
        value = re.sub(r'[^a-zA-Z]', ' ', value)
        value = re.sub(r'\s\s+', ' ', value)
        value = self.stemmer(value)
        value = self.sw_remover(value)
        return value