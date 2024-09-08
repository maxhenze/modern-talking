from argparse import ArgumentParser, Namespace
from typing import Iterable

from modern_talking.evaluation import Metric
from modern_talking.evaluation.f_measure import MacroF1Score, F1Score
from modern_talking.evaluation.manual_errors import ManualErrors
from modern_talking.evaluation.map import MeanAveragePrecision
from modern_talking.evaluation.precision import MacroPrecision, Precision
from modern_talking.evaluation.recall import MacroRecall, Recall
from modern_talking.matchers import LabelPolicy, Matcher
from modern_talking.pipeline import Pipeline

_metrics: Iterable[Metric] = [
    MeanAveragePrecision(),
    MeanAveragePrecision(new=True),
    Precision(),
    MacroPrecision(),
    Recall(),
    MacroRecall(),
    F1Score(),
    MacroF1Score(),
    ManualErrors(),
]


def _prepare_parser(parser: ArgumentParser) -> None:
    matcher_parsers = parser.add_subparsers(dest="matcher")
    parser.add_argument(
        dest="metric",
        type=str,
        choices=[metric.slug for metric in _metrics],
    )

    all_parser = matcher_parsers.add_parser("all")
    _prepare_all_parser(all_parser)

    none_parser = matcher_parsers.add_parser("none")
    _prepare_none_parser(none_parser)

    random_parser = matcher_parsers.add_parser("random")
    _prepare_random_parser(random_parser)

    term_overlap_parser = matcher_parsers.add_parser("term-overlap")
    _prepare_term_overlap_parser(term_overlap_parser)

    bilstm_parser = matcher_parsers.add_parser("bilstm-glove")
    _prepare_bilstm_parser(bilstm_parser)

    transformers_parser = matcher_parsers.add_parser("transformers")
    _prepare_transformers_parser(transformers_parser)

    parser.add_argument(
        "--test-unknown",
        dest="test_known",
        action="store_false",
        default=True,
    )
    parser.add_argument(
        "--test-known",
        dest="test_unknown",
        action="store_true",
        default=True,
    )


def _prepare_all_parser(_: ArgumentParser) -> None:
    pass


def _prepare_none_parser(_: ArgumentParser) -> None:
    pass


def _prepare_random_parser(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--seed",
        dest="seed",
        type=int,
    )


def _prepare_term_overlap_parser(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--stemming",
        dest="stemming",
        action="store_true",
    )
    parser.add_argument(
        "--stop-words",
        dest="stop_words",
        action="store_true",
    )
    parser.add_argument(
        "--custom-stop-words",
        dest="custom_stop_words",
        action="store_true",
    )
    parser.add_argument(
        "--synonyms",
        dest="synonyms",
        action="store_true",
    )
    parser.add_argument(
        "--antonyms",
        dest="antonyms",
        action="store_true",
    )
    parser.add_argument(
        "--language",
        dest="language",
        type=str,
        default="english",
    )


def _prepare_bilstm_parser(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--units",
        dest="units",
        type=int,
        default=16,
        help="Number of units in each BiLSTM module."
    )
    parser.add_argument(
        "--layers", "--depth",
        dest="layers",
        type=int,
        default=1,
        help="Number of BiLSTM layers."
    )
    parser.add_argument(
        "--max-length",
        dest="max_length",
        type=int,
        default=256,
    )
    parser.add_argument(
        "--dropout",
        dest="dropout",
        type=float,
        default=0.3,
    )
    parser.add_argument(
        "--learning-rate", "--learn",
        dest="learning_rate",
        type=float,
        default=1e-5,
    )
    parser.add_argument(
        "--weight-decay", "--decay",
        dest="weight_decay",
        type=float,
        default=1e-4,
    )
    parser.add_argument(
        "--shuffle",
        dest="shuffle",
        type=int,
        default=1000,
    )
    parser.add_argument(
        "--batch-size", "--batch",
        dest="batch_size",
        type=int,
        default=16,
    )
    parser.add_argument(
        "--epochs",
        dest="epochs",
        type=int,
        default=10,
    )
    parser.add_argument(
        "--early-stopping",
        dest="early_stopping",
        action="store_true",
    )
    parser.add_argument(
        "--augment",
        dest="augment",
        type=int,
        default=0,
    )
    parser.add_argument(
        "--label-policy",
        dest="label_policy",
        type=LabelPolicy,
        choices=list(LabelPolicy),
        default=LabelPolicy.skip,
    )
    parser.add_argument(
        "--strict",
        dest="label_policy",
        action="store_const",
        const=LabelPolicy.strict,
    )
    parser.add_argument(
        "--relaxed",
        dest="label_policy",
        action="store_const",
        const=LabelPolicy.relaxed,
    )


def _prepare_transformers_parser(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--model-type", "--type",
        dest="model_type",
        type=str,
        default="bert",
    )
    parser.add_argument(
        "--model-name", "--name",
        dest="model_name",
        type=str,
        default="bert-base-uncased",
    )
    parser.add_argument(
        "--max-sequence-length", "--max-length",
        dest="max_sequence_length",
        type=int,
        default=128,
    )
    parser.add_argument(
        "--augment",
        dest="augment",
        type=int,
        default=0,
    )
    parser.add_argument(
        "--label-policy",
        dest="label_policy",
        type=LabelPolicy,
        choices=list(LabelPolicy),
        default=LabelPolicy.skip,
    )
    parser.add_argument(
        "--strict",
        dest="label_policy",
        action="store_const",
        const=LabelPolicy.strict,
    )
    parser.add_argument(
        "--relaxed",
        dest="label_policy",
        action="store_const",
        const=LabelPolicy.relaxed,
    )
    parser.add_argument(
        "--over-sample",
        dest="over_sample",
        action="store_true",
    )
    parser.add_argument(
        "--shuffle",
        dest="shuffle",
        action="store_true",
    )
    parser.add_argument(
        "--batch-size", "--batch",
        dest="batch_size",
        type=int,
        default=16,
    )
    parser.add_argument(
        "--epochs",
        dest="epochs",
        type=int,
        default=1,
    )
    parser.add_argument(
        "--learning-rate",
        dest="learning_rate",
        type=float,
        default=4e-5,
    )
    parser.add_argument(
        "--warmup-ratio", "--warmup",
        dest="warmup_ratio",
        type=float,
        default=0.06,
    )
    parser.add_argument(
        "--weight-decay", "--decay",
        dest="weight_decay",
        type=float,
        default=0,
    )
    parser.add_argument(
        "--early-stopping",
        dest="early_stopping",
        action="store_true",
    )
    parser.add_argument(
        "--random-seed", "--seed",
        dest="random_seed",
        type=int,
        default=1234,
    )


def _create_pipeline(args: Namespace) -> Pipeline:
    metric: Metric = next(filter(lambda m: m.slug == args.metric, _metrics))

    matcher: Matcher

    if args.matcher == "all":
        from modern_talking.matchers.baselines import AllMatcher
        matcher = AllMatcher()

    elif args.matcher == "none":
        from modern_talking.matchers.baselines import NoneMatcher
        matcher = NoneMatcher()

    elif args.matcher == "random":
        from modern_talking.matchers.baselines import RandomMatcher
        matcher = RandomMatcher(
            seed=args.seed
        )

    elif args.matcher == "term-overlap":
        from modern_talking.matchers.term_overlap import TermOverlapMatcher
        matcher = TermOverlapMatcher(
            stemming=args.stemming,
            stop_words=args.stop_words,
            custom_stop_words=args.custom_stop_words,
            synonyms=args.synonyms,
            antonyms=args.antonyms,
            language=args.language,
        )
    elif args.matcher == "bilstm-glove":
        from modern_talking.matchers.bilstm import BidirectionalLstmMatcher
        matcher = BidirectionalLstmMatcher(
            units=args.units,
            layers=args.layers,
            max_length=args.max_length,
            dropout=args.dropout,
            learning_rate=args.learning_rate,
            weight_decay=args.weight_decay,
            shuffle=args.shuffle,
            batch_size=args.batch_size,
            epochs=args.epochs,
            early_stopping=args.early_stopping,
            augment=args.augment,
            label_policy=args.label_policy,
        )
    elif args.matcher == "transformers":
        from modern_talking.matchers.transformers import TransformersMatcher
        matcher = TransformersMatcher(
            model_type=args.model_type,
            model_name=args.model_name,
            max_sequence_length=args.max_sequence_length,
            augment=args.augment,
            label_policy=args.label_policy,
            over_sample=args.over_sample,
            shuffle=args.shuffle,
            batch_size=args.batch_size,
            epochs=args.epochs,
            learning_rate=args.learning_rate,
            warmup_ratio=args.warmup_ratio,
            weight_decay=args.weight_decay,
            early_stopping=args.early_stopping,
            random_seed=args.random_seed,
        )
    else:
        raise Exception("Invalid matcher.")

    return Pipeline(matcher, metric)


def parse_pipeline_cli() -> Pipeline:
    argument_parser: ArgumentParser = ArgumentParser()
    _prepare_parser(argument_parser)
    return _create_pipeline(argument_parser.parse_args())
