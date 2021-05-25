from os import system
from pathlib import Path
from pickle import dump, load
from typing import List
from tqdm import tqdm

from nltk.downloader import Downloader
from nltk.stem import SnowballStemmer
from nltk.tokenize import word_tokenize
from numpy import array
from sklearn.ensemble import VotingClassifier
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from spacy import Language, load as spacy_load
from spacy.util import is_package

from modern_talking.matchers import Matcher
from modern_talking.model import Dataset, Labels, Argument, KeyPoint
from modern_talking.model import LabelledDataset

downloader = Downloader()


class SVCPartOfSpeechMatcher(Matcher):
    name = "svc-bow-pos"
    model: SVC = None
    encoder: CountVectorizer = None
    language: Language

    def prepare(self) -> None:
        if not is_package("en_core_web_sm"):
            system("python -m spacy download en_core_web_sm")
        self.language = spacy.load("en_core_web_sm")
        return

    def get_token_by_pos(self, text: str) -> str:
        doc = self.language(text)
        pos_list = []
        selected_pos = ["ADJ", "ADV", "AUX", "NOUN", "PRON", "PROPN", "VERB"]
        for token in doc:
            if token.pos_ in selected_pos:
                pos_list.append(token.text)
        return " ".join(pos_list)

    def load_model(self, path: Path) -> bool:
        if self.model is not None and self.encoder is not None:
            return True
        if not path.exists() or not path.is_file():
            return False
        with path.open("rb") as file:
            self.model, self.encoder = load(file)
            return True

    def save_model(self, path: Path):
        with path.open("wb") as file:
            dump((self.model, self.encoder), file)

    def get_texts(self, train_data: LabelledDataset) -> List[str]:
        stemmer = SnowballStemmer("english")
        train_texts: List[str] = []
        for i in tqdm(range(len(list(train_data.labels.items())))):
            (arg_id, kp_id), label = list(train_data.labels.items())[i]
            arg = next(arg for arg in train_data.arguments if arg.id == arg_id)
            kp = next(kp for kp in train_data.key_points if kp.id == kp_id)
            arg_terms = [
                stemmer.stem(term)
                for term in word_tokenize(self.get_token_by_pos(arg.text))
            ]
            kp_terms = [
                stemmer.stem(term)
                for term in word_tokenize(self.get_token_by_pos(kp.text))
            ]

            text = " ".join(arg_terms) + ". " + " ".join(kp_terms)
            train_texts.append(text)
        return train_texts

    def train(self, train_data: LabelledDataset, dev_data: LabelledDataset):

        self.train_encoder(train_data)

        train_features = self.encoder.transform(self.get_texts(train_data))
        train_labels = array(list(train_data.labels.values()))

        svc = SVC(probability=True)
        self.model = svc
        self.model.fit(train_features, train_labels)

    def train_encoder(self, train_data: LabelledDataset):
        train_texts = self.get_texts(train_data)
        self.encoder = CountVectorizer()  # token_pattern="^[a-zA-Z]{3,7}$")
        self.encoder.fit_transform(train_texts)

    def get_match_probability(self, argument: Argument, key_point: KeyPoint):
        # Transform input text to numeric features.
        stemmer = SnowballStemmer("english")
        input_text = argument.text + ". " + key_point.text
        input_text = self.get_token_by_pos(input_text)
        input_text = " ".join(
            [stemmer.stem(term) for term in word_tokenize(input_text)]
        )
        features = self.encoder.transform([input_text]).toarray()
        # Predict label and probability with pretrained model.
        probability = self.model.predict_proba(features)
        score = probability[0][1]  # get probability of class 1
        return score

    def predict(self, data: Dataset) -> Labels:
        return {
            (arg.id, kp.id): self.get_match_probability(arg, kp)
            for arg in data.arguments
            for kp in data.key_points
            if arg.topic == kp.topic and arg.stance == kp.stance
        }


class EnsemblePartOfSpeechMatcher(Matcher):
    name = "ensemble-bow-pos"

    model: VotingClassifier = None
    encoder: CountVectorizer = None
    language: Language

    def prepare(self) -> None:
        # Install NLTK punctuation for tokenization.
        if not downloader.is_installed("punkt"):
            downloader.download("punkt")
        # Install English spaCy model.
        if not is_package("en_core_web_sm"):
            system("python -m spacy download en_core_web_sm")
        self.language = spacy_load("en_core_web_sm")

    def get_token_by_pos(self, text: str) -> str:
        doc = self.language(text)
        pos_list = []
        selected_pos = ["ADJ", "ADV", "AUX", "NOUN", "PRON", "PROPN", "VERB"]
        for token in doc:
            if token.pos_ in selected_pos:
                pos_list.append(token.text)
        return " ".join(pos_list)

    def load_model(self, path: Path) -> bool:
        if self.model is not None and self.encoder is not None:
            return True
        if not path.exists() or not path.is_file():
            return False
        with path.open("rb") as file:
            self.model, self.encoder = load(file)
            return True

    def save_model(self, path: Path):
        with path.open("wb") as file:
            dump((self.model, self.encoder), file)

    def get_texts(self, train_data: LabelledDataset) -> List[str]:
        stemmer = SnowballStemmer("english")
        train_texts: List[str] = []
        print("Token selection by POS")
        for i in tqdm(range(len(list(train_data.labels.items())))):
            (arg_id, kp_id), label = list(train_data.labels.items())[i]
            arg = next(arg for arg in train_data.arguments if arg.id == arg_id)
            kp = next(kp for kp in train_data.key_points if kp.id == kp_id)
            arg_terms = [
                stemmer.stem(term)
                for term in word_tokenize(self.get_token_by_pos(arg.text))
            ]
            kp_terms = [
                stemmer.stem(term)
                for term in word_tokenize(self.get_token_by_pos(kp.text))
            ]

            text = " ".join(arg_terms) + ". " + " ".join(kp_terms)
            train_texts.append(text)
        return train_texts

    def train(self, train_data: LabelledDataset, dev_data: LabelledDataset):

        self.train_encoder(train_data)

        train_features = self.encoder.transform(self.get_texts(train_data))
        train_labels = array(list(train_data.labels.values()))

        log_regression = LogisticRegression(
            # penalty='l2',
            C=14.0,
            verbose=1,
            max_iter=2000,
            # random_state=42,
        )
        svc = SVC(probability=True)
        self.model = VotingClassifier(
            estimators=[("lr", log_regression), ("svc", svc)],
            voting="soft",
            weights=[0.45, 0.55],
        )
        self.model.fit(train_features, train_labels)

    def train_encoder(self, train_data: LabelledDataset):
        train_texts = self.get_texts(train_data)
        self.encoder = CountVectorizer()  # token_pattern="^[a-zA-Z]{3,7}$")
        self.encoder.fit_transform(train_texts)

    def get_match_probability(self, argument: Argument, key_point: KeyPoint):
        # Transform input text to numeric features.
        stemmer = SnowballStemmer("english")
        input_text = argument.text + ". " + key_point.text
        input_text = self.get_token_by_pos(input_text)
        input_text = " ".join(
            [stemmer.stem(term) for term in word_tokenize(input_text)]
        )
        features = self.encoder.transform([input_text]).toarray()
        # Predict label and probability with pretrained model.
        probability = self.model.predict_proba(features)
        score = probability[0][1]  # get probability of class 1
        return score

    def predict(self, data: Dataset) -> Labels:
        return {
            (arg.id, kp.id): self.get_match_probability(arg, kp)
            for arg in data.arguments
            for kp in data.key_points
            if arg.topic == kp.topic and arg.stance == kp.stance
        }


class RegressionPartOfSpeechMatcher(Matcher):
    name = "regression-bow-pos"

    model: LogisticRegression = None
    encoder: CountVectorizer = None
    language: Language

    def prepare(self) -> None:
        if not is_package("en_core_web_sm"):
            system("python -m spacy download en_core_web_sm")
        self.language = spacy.load("en_core_web_sm")
        return

    def get_token_by_pos(self, text: str) -> str:
        doc = self.language(text)
        pos_list = []
        selected_pos = ["ADJ", "ADV", "AUX", "NOUN", "PRON", "PROPN", "VERB"]
        for token in doc:
            if token.pos_ in selected_pos:
                pos_list.append(token.text)
        return " ".join(pos_list)

    def load_model(self, path: Path) -> bool:
        if self.model is not None and self.encoder is not None:
            return True
        if not path.exists() or not path.is_file():
            return False
        with path.open("rb") as file:
            self.model, self.encoder = load(file)
            return True

    def save_model(self, path: Path):
        with path.open("wb") as file:
            dump((self.model, self.encoder), file)

    def get_texts(self, train_data: LabelledDataset) -> List[str]:
        stemmer = SnowballStemmer("english")
        train_texts: List[str] = []
        print("Token selection by POS")
        for i in tqdm(range(len(list(train_data.labels.items())))):
            (arg_id, kp_id), label = list(train_data.labels.items())[i]
            arg = next(arg for arg in train_data.arguments if arg.id == arg_id)
            kp = next(kp for kp in train_data.key_points if kp.id == kp_id)
            arg_terms = [
                stemmer.stem(term)
                for term in word_tokenize(self.get_token_by_pos(arg.text))
            ]
            kp_terms = [
                stemmer.stem(term)
                for term in word_tokenize(self.get_token_by_pos(kp.text))
            ]

            text = " ".join(arg_terms) + ". " + " ".join(kp_terms)
            train_texts.append(text)
        return train_texts

    def train(self, train_data: LabelledDataset, dev_data: LabelledDataset):

        self.train_encoder(train_data)

        train_features = self.encoder.transform(self.get_texts(train_data))
        train_labels = array(list(train_data.labels.values()))

        log_regression = LogisticRegression(
            # penalty='l2',
            C=14.0,
            verbose=1,
            max_iter=2000,
            # random_state=42,
        )
        self.model = log_regression
        self.model.fit(train_features, train_labels)

    def train_encoder(self, train_data: LabelledDataset):
        train_texts = self.get_texts(train_data)
        self.encoder = CountVectorizer()  # token_pattern="^[a-zA-Z]{3,7}$")
        self.encoder.fit_transform(train_texts)

    def get_match_probability(self, argument: Argument, key_point: KeyPoint):
        # Transform input text to numeric features.
        stemmer = SnowballStemmer("english")
        input_text = argument.text + ". " + key_point.text
        input_text = self.get_token_by_pos(input_text)
        input_text = " ".join(
            [stemmer.stem(term) for term in word_tokenize(input_text)]
        )
        features = self.encoder.transform([input_text]).toarray()
        # Predict label and probability with pretrained model.
        probability = self.model.predict_proba(features)
        score = probability[0][1]  # get probability of class 1
        return score

    def predict(self, data: Dataset) -> Labels:
        return {
            (arg.id, kp.id): self.get_match_probability(arg, kp)
            for arg in data.arguments
            for kp in data.key_points
            if arg.topic == kp.topic and arg.stance == kp.stance
        }


class EnsembleVotingMatcher(Matcher):
    name = "ensemble-bow-voting"

    model: VotingClassifier = None
    encoder: CountVectorizer = None

    def prepare(self) -> None:
        # Install NLTK punctuation for tokenization.
        if not downloader.is_installed("punkt"):
            downloader.download("punkt")

    def load_model(self, path: Path) -> bool:
        if self.model is not None and self.encoder is not None:
            return True
        if not path.exists() or not path.is_file():
            return False
        with path.open("rb") as file:
            self.model, self.encoder = load(file)
            return True

    def save_model(self, path: Path):
        with path.open("wb") as file:
            dump((self.model, self.encoder), file)

    def train(self, train_data: LabelledDataset, dev_data: LabelledDataset):
        """
        Encode training data with bag of words to get numeric features.
        Then use ensemble of two classifiers: Logistic Regression and SVM
        classifiers have different weights for prediction.
        """
        self.train_encoder(train_data)

        train_features = self.encoder.transform(get_texts(train_data))
        train_labels = array(list(train_data.labels.values()))

        log_regression = LogisticRegression(
            # penalty='l2',
            C=16.0,
            verbose=1,
            max_iter=2000,
            # random_state=42,
        )
        svc = SVC(probability=True)
        self.model = VotingClassifier(
            estimators=[("lr", log_regression), ("svc", svc)],
            voting="soft",
            weights=[0.55, 0.45],
        )
        self.model.fit(train_features, train_labels)

    def train_encoder(self, train_data: LabelledDataset):
        train_texts = get_texts(train_data)
        self.encoder = CountVectorizer()  # token_pattern="^[a-zA-Z]{3,7}$")
        self.encoder.fit_transform(train_texts)

    def get_match_probability(self, argument: Argument, key_point: KeyPoint):
        # Transform input text to numeric features.
        stemmer = SnowballStemmer("english")
        input_text = argument.text + " " + key_point.text
        input_text = " ".join(
            [stemmer.stem(term) for term in word_tokenize(input_text)]
        )
        features = self.encoder.transform([input_text]).toarray()
        # Predict label and probability with pretrained model.
        probability = self.model.predict_proba(features)
        score = probability[0][1]  # get probability of class 1
        return score

    def predict(self, data: Dataset) -> Labels:
        return {
            (arg.id, kp.id): self.get_match_probability(arg, kp)
            for arg in data.arguments
            for kp in data.key_points
            if arg.topic == kp.topic and arg.stance == kp.stance
        }


def get_texts(train_data: LabelledDataset) -> List[str]:
    stemmer = SnowballStemmer("english")
    train_texts: List[str] = []
    for (arg_id, kp_id), label in train_data.labels.items():
        arg = next(arg for arg in train_data.arguments if arg.id == arg_id)
        kp = next(kp for kp in train_data.key_points if kp.id == kp_id)
        arg_terms = [stemmer.stem(term) for term in word_tokenize(arg.text)]
        kp_terms = [stemmer.stem(term) for term in word_tokenize(kp.text)]
        text = " ".join(arg_terms) + " " + " ".join(kp_terms)
        train_texts.append(text)
    return train_texts


class RegressionTfidfMatcher(Matcher):
    name = "regression-tfidf"

    model: LogisticRegression = None
    encoder: TfidfVectorizer = None

    def prepare(self) -> None:
        # Install NLTK punctuation for tokenization.
        if not downloader.is_installed("punkt"):
            downloader.download("punkt")

    def load_model(self, path: Path) -> bool:
        if self.model is not None and self.encoder is not None:
            return True
        if not path.exists() or not path.is_file():
            return False
        with path.open("rb") as file:
            self.model, self.encoder = load(file)
            return True

    def save_model(self, path: Path):
        with path.open("wb") as file:
            dump((self.model, self.encoder), file)

    def train(self, train_data: LabelledDataset, dev_data: LabelledDataset):
        """
        Encode training data with bag of words to get numeric features.
        Then use ensemble of two classifiers: Logistic Regression and SVM
        classifiers have different weights for prediction.
        """
        self.train_encoder(train_data)

        train_features = self.encoder.transform(get_texts(train_data))
        train_labels = array(list(train_data.labels.values()))

        log_regression = LogisticRegression(
            # penalty='l2',
            C=16.0,
            verbose=1,
            max_iter=2000,
            # random_state=42,
        )
        self.model = log_regression
        self.model.fit(train_features, train_labels)

    def train_encoder(self, train_data: LabelledDataset):
        train_texts = get_texts(train_data)
        self.encoder = TfidfVectorizer()
        self.encoder.fit_transform(train_texts)

    def get_match_probability(self, argument: Argument, key_point: KeyPoint):
        # Transform input text to numeric features.
        stemmer = SnowballStemmer("english")
        input_text = argument.text + " " + key_point.text
        input_text = " ".join(
            [stemmer.stem(term) for term in word_tokenize(input_text)]
        )
        features = self.encoder.transform([input_text]).toarray()
        # Predict label and probability with pretrained model.
        probability = self.model.predict_proba(features)
        score = probability[0][1]  # get probability of class 1
        return score

    def predict(self, data: Dataset) -> Labels:
        return {
            (arg.id, kp.id): self.get_match_probability(arg, kp)
            for arg in data.arguments
            for kp in data.key_points
            if arg.topic == kp.topic and arg.stance == kp.stance
        }


class RegressionBagOfWordsMatcher(Matcher):
    """
    Return probabilities as matching scores.
    TODO Document matcher.
    """

    name = "regression-bow"

    model: LogisticRegression = None
    encoder: CountVectorizer = None

    def prepare(self) -> None:
        # Install NLTK punctuation for tokenization.
        if not downloader.is_installed("punkt"):
            downloader.download("punkt")

    def load_model(self, path: Path) -> bool:
        if self.model is not None and self.encoder is not None:
            return True
        if not path.exists() or not path.is_file():
            return False
        with path.open("rb") as file:
            self.model, self.encoder = load(file)
            return True

    def save_model(self, path: Path):
        with path.open("wb") as file:
            dump((self.model, self.encoder), file)

    def train(self, train_data: LabelledDataset, dev_data: LabelledDataset):
        """
        Encode training data with bag of words to get numeric features.
        Then use ensemble of two classifiers: Logistic Regression and SVM
        classifiers have different weights for prediction.
        """
        self.train_encoder(train_data)

        train_features = self.encoder.transform(get_texts(train_data))
        train_labels = array(list(train_data.labels.values()))

        log_regression = LogisticRegression(
            # penalty='l2',
            C=16.0,
            verbose=1,
            max_iter=2000,
            # random_state=42,
        )
        self.model = log_regression
        self.model.fit(train_features, train_labels)

    def train_encoder(self, train_data: LabelledDataset):
        train_texts = get_texts(train_data)
        self.encoder = CountVectorizer()
        self.encoder.fit_transform(train_texts)

    def get_match_probability(self, argument: Argument, key_point: KeyPoint):
        # Transform input text to numeric features.
        stemmer = SnowballStemmer("english")
        input_text = argument.text + " " + key_point.text
        input_text = " ".join(
            [stemmer.stem(term) for term in word_tokenize(input_text)]
        )
        features = self.encoder.transform([input_text]).toarray()
        # Predict label and probability with pretrained model.
        probability = self.model.predict_proba(features)
        score = probability[0][1]  # get probability of class 1
        return score

    def predict(self, data: Dataset) -> Labels:
        return {
            (arg.id, kp.id): self.get_match_probability(arg, kp)
            for arg in data.arguments
            for kp in data.key_points
            if arg.topic == kp.topic and arg.stance == kp.stance
        }


class SVCBagOfWordsMatcher(Matcher):
    name = "svc-bow"

    model: SVC = None
    encoder: CountVectorizer = None

    def load_model(self, path: Path) -> bool:
        if self.model is not None and self.encoder is not None:
            return True
        if not path.exists() or not path.is_file():
            return False
        with path.open("rb") as file:
            self.model, self.encoder = load(file)
            return True

    def save_model(self, path: Path):
        with path.open("wb") as file:
            dump((self.model, self.encoder), file)

    def train(self, train_data: LabelledDataset, dev_data: LabelledDataset):
        """
        Encode training data with bag of words to get numeric features.
        Then use ensemble of two classifiers: Logistic Regression and SVM
        classifiers have different weights for prediction.
        """
        self.train_encoder(train_data)
        train_features = self.encoder.transform(get_texts(train_data))
        train_labels = array(list(train_data.labels.values()))
        svc = SVC(probability=True)
        self.model = svc
        self.model.fit(train_features, train_labels)

    def train_encoder(self, train_data: LabelledDataset):
        train_texts = get_texts(train_data)
        self.encoder = CountVectorizer()
        self.encoder.fit_transform(train_texts)

    def get_match_probability(self, argument: Argument, key_point: KeyPoint):
        # Transform input text to numeric features.
        stemmer = SnowballStemmer("english")
        input_text = argument.text + " " + key_point.text
        input_text = " ".join(
            [stemmer.stem(term) for term in word_tokenize(input_text)]
        )
        features = self.encoder.transform([input_text]).toarray()
        # Predict label and probability with pretrained model.
        probability = self.model.predict_proba(features)
        score = probability[0][1]  # get probability of class 1
        return score

    def predict(self, data: Dataset) -> Labels:
        return {
            (arg.id, kp.id): self.get_match_probability(arg, kp)
            for arg in data.arguments
            for kp in data.key_points
            if arg.topic == kp.topic and arg.stance == kp.stance
        }
