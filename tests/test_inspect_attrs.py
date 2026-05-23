def test_inspect_attrs():
    from NoWires.algorithm.coverage_comparison import CoverageComparisonAlgorithm
    a = CoverageComparisonAlgorithm()
    for attr_name in sorted(dir(a)):
        if 'PANEL' in attr_name or 'GRID' in attr_name:
            if not attr_name.startswith('_'):
                print(f'  {attr_name} = {getattr(a, attr_name, "ERROR")}')
