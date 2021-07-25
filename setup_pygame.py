import glob 
import os 
import sys 
import random
import weakref
try:
    sys.path.append(glob.glob('../carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass

import carla 
width = 1280
height = 780

from carla import ColorConverter as cc 

try:

	import pygame
	from pygame.locals import KMOD_CTRL
	from pygame.locals import KMOD_SHIFT
	from pygame.locals import K_0
	from pygame.locals import K_9
	from pygame.locals import K_BACKQUOTE
	from pygame.locals import K_BACKSPACE
	from pygame.locals import K_COMMA
	from pygame.locals import K_DOWN
	from pygame.locals import K_ESCAPE
	from pygame.locals import K_F1
	from pygame.locals import K_LEFT
	from pygame.locals import K_PERIOD
	from pygame.locals import K_RIGHT
	from pygame.locals import K_SLASH
	from pygame.locals import K_SPACE
	from pygame.locals import K_TAB
	from pygame.locals import K_UP
	from pygame.locals import K_a
	from pygame.locals import K_b
	from pygame.locals import K_c
	from pygame.locals import K_d
	from pygame.locals import K_g
	from pygame.locals import K_h
	from pygame.locals import K_i
	from pygame.locals import K_l
	from pygame.locals import K_m
	from pygame.locals import K_n
	from pygame.locals import K_p
	from pygame.locals import K_q
	from pygame.locals import K_r
	from pygame.locals import K_s
	from pygame.locals import K_v
	from pygame.locals import K_w
	from pygame.locals import K_x
	from pygame.locals import K_z
	from pygame.locals import K_MINUS
	from pygame.locals import K_EQUALS


except:
	raise RuntimeError('cannot import pygame , make sure pygame package is not installed')

import numpy as np

class World:

	def __init__(self, carla_world):

		self.world = carla_world
		self.map = self.world.get_map()
		self.camera_manager = None

		self.gamma  = 2.2 
		self.player = None
		self.restart() 

	def restart(self):

		cam_index = self.camera_manager.index if self.camera_manager is not None else 0

		blueprint = self.world.get_blueprint_library().filter('cybertruck')[0]

		if self.player is not None:

			spawn_point = self.player.get_transform()
			spawn_point.location.z +=20
			spawn_point.location.roll = 0.0
			spawn_point.location.pitch = 0.0
			self.destroy()
			self.player = self.world.try_spawn_actor(blueprint,spawn_point)

		while self.player is  None:

			if not self.map.get_spawn_points():
				print(' there are non spawn_points in ur map')

			spawn_points = self.map.get_spawn_points()

			spawn_point = random.choice(spawn_points) if spawn_points else carla.Transform()
			self.player = self.world.try_spawn_actor(blueprint , spawn_point)

		self.camera_manager = CameraManager(self.player , self.gamma)
		self.camera_manager.set_sensor(cam_index)

	def render(self , display):
		self.camera_manager.render(display)


	def destroy(self):

		sensor = [self.camera_manager.sensor]

		for sensor in sensors:
			if sensor is not None:
				sensor.stop()
				sensor.destroy()

		if self.player is not None:

			self.player.destroy()

	def destroy_sensors(self):

		self.camera_manager.sensor.destroy()
		self.camera_manager.sensor = None
		self.camera_manager.index = None

class KeyboardControl(object):

	def __init__(self ,world):
		self.set_autopilot = False
		self.control = carla.VehicleControl()
		self.steer_cache = 0.0

	def parse_events(self , client ,  world , clock ):

		for event in pygame.event.get():

			if event.type == pygame.KEYUP:

				if self._is_quit_shortcut(event.key):
					return True

				elif event.key == K_BACKSPACE:

					world.restart()

				elif event.key == K_BACKQUOTE:
					world.camera_manager.next_sensor()

			if isinstance(self.control , carla.VehicleControl):

				self.parse_vehicle_keys(pygame.key.get_pressed() , clock.get_time())

			world.player.apply_control(self.control)



	def parse_vehicle_keys(self , keys , milliseconds):

		if keys[K_UP] or keys[K_w]:

			self.control.throttle = min(self.control.throttle+0.01 , 1)

		else :
			self.control.throttle = 0.0

		if keys[K_DOWN] or keys[K_s]:
			self.control.brake = min(self.control.brake+0.2,1)

		else:
			self.control.brake = 0.0
		print('milliseconds' , milliseconds)
		steer_increment = 5e-4

		if keys[K_LEFT] or keys[K_a]:
			print('left')
			if self.steer_cache >0:
				self.steer_cache = 0

			else:
				self.steer_cache -= steer_increment

		elif keys[K_RIGHT] or keys[K_d]:
			print('right')
			if self.steer_cache<0:
				self.steer_cache = 0

			else:
				self.steer_cache+=steer_increment

		else:
			self.steer_cache =0.0	

		self.steer_cache = min(0.7 , max(-0.7 ,self.steer_cache))
		print(self.steer_cache , 'steer_cache')
		self.control.steer = round(self.steer_cache ,1)


	@staticmethod
	def _is_quit_shortcut(key):

		return (key==K_ESCAPE) or (key==K_q and pygame.key.get_mods() & KMOD_CTRL)	


class CameraManager(object):
	def __init__(self, parent_actor , gamma_correction):

		self.sensor = None
		self.surface = None 
		self.parent = parent_actor
		Attachment = carla.AttachmentType
		self.transform_index = 0
		self._camera_transforms = [(carla.Transform(carla.Location(x=1.5 , z= 2.4)), Attachment.Rigid )]

		self.sensors  = [
		['sensor.camera.rgb',cc.Raw , 'Camera RGB' , {}],
		['sensor.camera.depth' , cc.Raw , 'Camera Depth(Raw)' , {}],
		['sensor.camera.semantic_segmentation' , cc.CityScapesPalette , ' Camera Semantic Segmentation (CityScapes Palette)',{}] 
		]

		world = self.parent.get_world()
		bp_library = world.get_blueprint_library()

		for item in self.sensors:

			bp = bp_library.find(item[0])
			if item[0].startswith('sensor.camera'):

				bp.set_attribute('image_size_x' , str(width))
				bp.set_attribute('image_size_y' , str(height))
				if bp.has_attribute('gamma'):
					bp.set_attribute('gamma' , str(gamma_correction))

			item.append(bp)

		self.index = None

	def set_sensor(self , index , notify = True , force_respawn = False):

		index = index % len(self.sensors)

		needs_respawn = True if self.index is None else (force_respawn or (self.sensors[index][2]!= self.sensors[self.index][2]))

		if needs_respawn:

			if self.sensor is not None:
				self.sensor.destroy()
				self.surface = None

			self.sensor = self.parent.get_world().spawn_actor(self.sensors[index][-1] , self._camera_transforms[self.transform_index][0] , attach_to  = self.parent , attachment_type = self._camera_transforms[self.transform_index][1])
			weak_self = weakref.ref(self)

			self.sensor.listen(lambda image : CameraManager._parse_image(weak_self , image))

		self.index = index

	def next_sensor(self):
		self.set_sensor(self.index+1)


	def render(self , display):
		if self.surface is not None:
			display.blit(self.surface , (0,0))

	@staticmethod
	def _parse_image(weak_self , image):
		self = weak_self()
		if not self:
			return
		if self.sensors[self.index][0].startswith('sensor.lidar'):
			pass

		else:

			image.convert(self.sensors[self.index][1])
			img = np.frombuffer(image.raw_data , dtype = np.dtype("uint8"))
			img = np.reshape(img , (image.height , image.width , 4))
			array = img[:,:,:3]
			array = array[:,:,::-1]

			self.surface = pygame.surfarray.make_surface(array.swapaxes(0,1))


  

def game_loop():

	try:
		pygame.init()
		pygame.font.init()

		client = carla.Client('localhost' , 2000)
		client.set_timeout(10.0)

		display = pygame.display.set_mode((width , height) , pygame.HWSURFACE|pygame.DOUBLEBUF)

		clock = pygame.time.Clock()
		world = World(client.get_world())

		controller = KeyboardControl(world)
		while True:
			if controller.parse_events(client , world , clock):
				return
			world.render(display)
			pygame.display.flip()
	finally:

		pygame.quit()



game_loop()