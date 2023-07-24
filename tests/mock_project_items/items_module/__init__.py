from spine_engine.exception import ItemsVersionTooHigh


def _project_item_classes():
    from .test_item.project_item import TestProjectItem
    from .test_item_with_specification.project_item import TestSpecificationProjectItem

    return {
        TestProjectItem.item_type(): TestProjectItem,
        TestSpecificationProjectItem.item_type(): TestSpecificationProjectItem,
    }


PROJECT_ITEM_CLASSES = _project_item_classes()
LATEST_PROJECT_DICT_ITEMS_VERSION = 1


def upgrade_items_to_latest(item_dict, old_version):
    if old_version > LATEST_PROJECT_DICT_ITEMS_VERSION:
        raise ItemsVersionTooHigh()
    return item_dict
