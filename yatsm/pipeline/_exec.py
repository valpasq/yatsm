""" Functions for handling the execution of a pipeline graph
"""
import logging

from toolz import curry
from dask import delayed

from ._topology import config_to_tasks
from .language import OUTPUT, REQUIRE
from .tasks import pipeline_tasks

logger = logging.getLogger(__name__)


def curry_pipeline_task(func, spec):
    return curry(func,
                 **{REQUIRE: spec[REQUIRE],
                    OUTPUT: spec[OUTPUT],
                    'config': spec.get('config', {})})


def setup_pipeline(config, pipe):
    """ Process the configuration for a YATSM pipeline

    Args:
        config (dict): Pipeline configuration dictionary
        pipe (dict[str: dict]): Dictionary storing ``data`` and ``record``
            information. At this point, ``data`` and ``record`` can either
            store actual data (e.g., an `xarray.Dataset`) or simply a
            dictionary that mimics the data (i.e., it contains the same keys).

    Returns:
        list: List of curried, delayed functions ready to be ran in a pipeline
    """
    tasks = config_to_tasks(config, pipe)

    pipeline = []
    for task in tasks:
        # TODO: curry & delay these
        try:
            func = pipeline_tasks[config[task]['task']]
        except KeyError as exc:
            logger.error('Unknown pipeline task "{}" referenced in "{}"'
                         .format(config[task]['task'], task))
            raise
        pipeline.append(curry_pipeline_task(func, config[task]))

    return pipeline


def delay_pipeline(pipeline, pipe):
    """ Return a ``dask.delayed`` pipeline ready to execute

    Args:
        pipeline (list[callable]): A list of curried functions ready to be
            run using data from ``pipe``. This list may be constructed as the
            output of :ref:`setup_pipeline`, for example.
        pipe (dict): Dictionary storing ``data`` and ``record`` information.

    Returns:
        dask.delayed: A delayed pipeline ready to be executed
    """
    _pipeline = delayed(pipeline[0])(pipe)
    for task in pipeline[1:]:
        _pipeline = delayed(task)(_pipeline)

    return _pipeline