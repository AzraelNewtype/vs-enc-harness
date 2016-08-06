def preprin(foo):
    """Debug printing. It's not worth importing always, and lazier to type as needed."""
    import pprint
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(foo)