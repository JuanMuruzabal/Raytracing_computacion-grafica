import numpy as np

class ImageData:
    def __init__(self, width, height, channels, color= (0,0,0)):
        self.data = np.full((height, width, channels), color, dtype=np.uint8)
    def set_pixel(self, x, y, color):
        self.data[y, x] = color
    def tobytes(self):
        return self.data.tobytes()
    

class Texture:
    def __init__(self, name = "u_texture", width=1, height=1, channels_amount = 3, image_Data:ImageData = None,
                 color= (0,0,0), repeat_x = False, repeat_y = False, build_mipmaps = False):
        self.name = name
        self.size = (width, height)
        self.channels_amount = channels_amount
        self.repeat_x = repeat_x
        self.repeat_y = repeat_y
        self.build_mipmaps = build_mipmaps

        self.width = width
        self.height = height

        if image_Data is not None:
            self._image_data = image_Data
        else:
            self._image_data = ImageData(width, height, channels_amount, color)

    @property
    def image_data(self):
       return self._image_data
        
    def update_data(self, new_data: ImageData):
        self._image_data = new_data
    
    def set_pixel(self, x, y, color):
        self._image_data.set_pixel(x, y, color)

    def get_bytes(self):
        return self._image_data.tobytes()