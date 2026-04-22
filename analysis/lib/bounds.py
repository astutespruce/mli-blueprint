def bounds_overlap(left, right):
    return (left[0] <= right[2] and left[2] >= right[0]) or (
        left[1] <= right[3] and left[3] >= right[1]
    )
