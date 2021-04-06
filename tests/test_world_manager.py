from world_manager import world_manager


def test_dict_walker():
    sample_dict = {'part_1':[5,6,7],
               'part_2':[3,6,{'a':999,
                              'b':777,
                              'c':123}]}
    result = list(world_manager.dict_walker(sample_dict))
    assert result == [['part_1', 0, 5],
    ['part_1', 1, 6],
    ['part_1', 2, 7],
    ['part_2', 0, 3],
    ['part_2', 1, 6],
    ['part_2', 2, 'a', 999],
    ['part_2', 2, 'b', 777],
    ['part_2', 2, 'c', 123]]
