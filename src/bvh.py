import numpy as np


class BVHNode:

    def __init__(self, aabb_min=(0,0,0), aabb_max=(0,0,0), left=-1, right=-1, prim_start=-1, prim_count=0):

        self.aabb_min = tuple(aabb_min)

        self.aabb_max = tuple(aabb_max)

        self.left = left

        self.right = right

        self.primitive_start = prim_start

        self.primitive_count = prim_count


    def is_leaf(self):

        return self.primitive_count > 0


    def pack(self):

        left_val = float(self.left)

        if self.is_leaf():

            right_or_obj = float(self.primitive_start)

        else:

            right_or_obj = float(-self.right - 2) if self.right >= 0 else -1.0

        return [*self.aabb_min, left_val, *self.aabb_max, right_or_obj]



class BVH:

    def __init__(self, prims):

        self.prims = prims

        self.nodes = []

        # Handle empty primitives case
        if not prims:
            # Create a dummy node for empty scenes
            self.nodes = [BVHNode(aabb_min=(-1, -1, -1), aabb_max=(1, 1, 1))]
        else:
            self.build()


    def build(self):

        indices = list(range(len(self.prims)))


        def recurse(indexs):

            mins = [self.prims[i]['aabb_min'] for i in indexs]

            maxs = [self.prims[i]['aabb_max'] for i in indexs]

            node_min = (

                min(m[0] for m in mins),

                min(m[1] for m in mins),

                min(m[2] for m in mins)

            )

            node_max = (

                max(m[0] for m in maxs),

                max(m[1] for m in maxs),

                max(m[2] for m in maxs)

            )


            node_index = len(self.nodes)

            node = BVHNode(aabb_min=node_min, aabb_max=node_max)

            self.nodes.append(node)


            if len(indexs) == 1:

                node.primitive_start = indexs[0]

                node.primitive_count = 1

                return node_index


            extents = [node_max[i] - node_min[i] for i in range(3)]

            axis = max(range(3), key=lambda i: extents[i])


            indexs.sort(key=lambda i: (self.prims[i]['aabb_min'][axis] + self.prims[i]['aabb_max'][axis]) * 0.5)

            mid = len(indexs) // 2


            left = recurse(indexs[:mid])

            right = recurse(indexs[mid:])


            node.left = left

            node.right = right

            return node_index


        recurse(indices)


    def pack_to_bytes(self):

        floats = []

        for node in self.nodes:

            floats.extend(node.pack())

        return np.array(floats, dtype='f4').tobytes()
