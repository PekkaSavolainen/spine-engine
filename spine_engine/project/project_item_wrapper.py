######################################################################################################################
# Copyright (C) 2017-2022 Spine project consortium
# This file is part of Spine Engine.
# Spine Engine is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General
# Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option)
# any later version. This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General
# Public License for more details. You should have received a copy of the GNU Lesser General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.
######################################################################################################################
"""This module contains Spine Engine adapter for project items."""
from hashlib import sha1
import logging

from ..spine_engine import ItemExecutionFinishState
from ..utils.helpers import ExecutionDirection


class ProjectItemWrapper:
    """A Wrapper that glues project item into Spine Engine."""

    def __init__(self, name, project_item, group_id):
        """
        Args:
            name (str): name of time
            project_item (ProjectItem): project item to wrap
            group_id (str, optional): item's execution group id
        """
        self._name = name
        self._item = project_item
        self._group_id = project_item.name if group_id is None else group_id
        self._filter_id = ""
        logger = logging.getLogger(self.logger_name())
        self._logger = FilteredExecutionLogger(logger, name, self._item.item_type(), self._filter_id)

    @property
    def project_item(self):
        """Returns the wrapped project item."""
        return self._item

    @property
    def group_id(self):
        """Returns the id for group-execution.

        Items in the same group share a kernel, and also reuse the same kernel from past executions.
        By default, each item is its own group, so it executes in isolation.
        NOTE: At the moment this is only used by Tool, but could be used by other items in the future?

        Returns:
            str: item's id within an execution group
        """
        return self._group_id

    @property
    def filter_id(self):
        return self._filter_id

    @filter_id.setter
    def filter_id(self, filter_id):
        self._filter_id = filter_id
        self._logger.set_filter_id(filter_id)

    def hash_filter_id(self):
        """Hashes filter id.

        Returns:
            str: hash
        """
        return sha1(bytes(self._filter_id, "utf8")).hexdigest() if self._filter_id else ""

    def ready_to_execute(self, settings):
        """Validates the internal state of this project item before execution.

        Subclasses can implement this method to do the appropriate work.

        Args:
            settings (AppSettings): Application settings

        Returns:
            bool: True if project item is ready for execution, False otherwise
        """
        return True

    def update(self, forward_resources, backward_resources):
        """Executes tasks that should be done before going into a next iteration of the loop.

        Args:
            forward_resources (list of ProjectItemResource): resources received from upstream
            backward_resources (list of ProjectItemResource): resources received from downstream

        Returns:
            bool: True if update was successful, False otherwise
        """
        return True

    def execute(self, forward_resources, backward_resources, lock):
        """Executes this item using the given resources and returns a boolean indicating the outcome.

        Subclasses can implement this method to do the appropriate work.

        Args:
            forward_resources (list): a list of ProjectItemResources from predecessors (forward)
            backward_resources (list): a list of ProjectItemResources from successors (backward)
            lock (Lock): shared lock for parallel executions

        Returns:
            ItemExecutionFinishState: State depending on operation success
        """
        self._logger.info("Executing...")
        return ItemExecutionFinishState.SUCCESS

    def exclude_execution(self, forward_resources, backward_resources, lock):
        """Excludes execution of this item.

        This method is called when the item is not selected (i.e EXCLUDED) for execution.
        Only lightweight bookkeeping or processing should be done in this case, e.g.
        forward input resources.

        Subclasses can implement this method to do the appropriate work.

        Args:
            forward_resources (list): a list of ProjectItemResources from predecessors (forward)
            backward_resources (list): a list of ProjectItemResources from successors (backward)
            lock (Lock): shared lock for parallel executions
        """

    def finish_execution(self, state):
        """Does any work needed after execution given the execution success status.

        Args:
            state (ItemExecutionFinishState): Item execution finish state
        """
        if state == ItemExecutionFinishState.SUCCESS:
            self._logger.info("Finished", extra={"success": True})
        elif state == ItemExecutionFinishState.FAILURE:
            self._logger.error("Failed")
        elif state == ItemExecutionFinishState.SKIPPED:
            self._logger.warning("Skipped")
        elif state == ItemExecutionFinishState.STOPPED:
            self._logger.error("Stopped")
        else:
            self._logger.error("Finished execution in an unknown state")

    @staticmethod
    def is_filter_terminus():
        """Tests if the item 'terminates' a forked execution.

        Returns:
            bool: True if forked executions should be joined before the item, False otherwise
        """
        return False

    def output_resources(self, direction):
        """Returns output resources in the given direction.

        Subclasses need to implement _output_resources_backward and/or _output_resources_forward
        if they want to provide resources in any direction.

        Args:
            direction (ExecutionDirection): Direction where output resources are passed

        Returns:
            list: a list of ProjectItemResources
        """
        return {
            ExecutionDirection.BACKWARD: self._output_resources_backward,
            ExecutionDirection.FORWARD: self._output_resources_forward,
        }[direction]()

    def stop_execution(self):
        """Stops executing this item."""
        self._logger.info(f"Stopping...")

    # pylint: disable=no-self-use
    def _output_resources_forward(self):
        """Returns output resources for forward execution.

        The default implementation returns an empty list.

        Returns:
            list: a list of ProjectItemResources
        """
        return []

    # pylint: disable=no-self-use
    def _output_resources_backward(self):
        """Returns output resources for backward execution.

        The default implementation returns an empty list.

        Returns:
            list: a list of ProjectItemResources
        """
        return []

    @staticmethod
    def logger_name():
        """Returns item logger name.

        Returns:
            str: logger's name
        """
        return __name__


class FilteredExecutionLogger(logging.LoggerAdapter):
    """Logger adapter that adds filter id to the log message."""

    def __init__(self, logger, item_name, item_type, filter_id):
        """
        Args:
            logger (Logger): logger instance
            item_name (str): project item's name
            item_type (str): project item's type
            filter_id (str): filter id
        """
        super().__init__(logger, {"item_name": item_name, "item_type": item_type, "filter_id": filter_id})

    def set_filter_id(self, filter_id):
        """Sets new filter id.

        Args:
            filter_id (str): filter id,
        """
        self.extra["filter_id"] = filter_id
