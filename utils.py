def rindex(lst, value):
    try:
        return len(lst) - lst[::-1].index(value) - 1
    except ValueError:
        raise ValueError(f"{value} is not in list")
