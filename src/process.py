###############################
# THIS CODE IS RAN IN BLENDER #
###############################

import sys
import bpy
import math
import bmesh
import os
import time

argv = sys.argv
argv = argv[argv.index("--") + 1:]
filepath = argv[0]
output_dir = argv[1]

# /////////// PROGRESS BAR INITIALIZATION /////////// #

def update_progress(filepath, value, message):
    progress_path = os.path.join(os.path.dirname(filepath), "progress.txt")
    with open(progress_path, "w") as f:
        f.write(f"{value}\n{message}")
    #cheeky little sleep so the status's show up so it looks cool lol
    time.sleep(0.05)

# /////////// PREPARE OBJECT /////////// #

#DELETE ALL OBJECTS AND MATERIALS
#PROGRESS_UPDATE--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/
update_progress(filepath, 6, "Initializing")


bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

for mat in list(bpy.data.materials):
    bpy.data.materials.remove(mat)

#IMPORT THE MESH
#PROGRESS_UPDATE--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/
update_progress(filepath, 12, "Importing Mesh")

bpy.ops.wm.obj_import(filepath=filepath)

print(bpy.context.selected_objects)

#SET OBJECT TO CENTER OF WORLD
#PROGRESS_UPDATE--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/
update_progress(filepath, 18, "Preparing Mesh")

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
bpy.ops.object.location_clear()

#MERGE VERTS BY DISTANCE KEEPING SHARPS
#PROGRESS_UPDATE--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/
update_progress(filepath, 24, "Merging Vertices")

obj = bpy.context.selected_objects[0]
bpy.context.view_layer.objects.active = obj

bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=0.0001, use_sharp_edge_from_normals=True)
bpy.ops.object.mode_set(mode='OBJECT')

# /////////// PREPARE TEXTURE /////////// #
#PROGRESS_UPDATE--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/
update_progress(filepath, 30, "Preparing Texture")

#FIND TOTAL NUMBER OF UNIQE COLORS. DONT WASTE TEXTURE SPACE ON DUPLICATES
colors = set()
for mat in obj.data.materials:
    c = mat.diffuse_color
    rounded = tuple(round(v, 2) for v in c[:3])
    colors.add(rounded)

print(f"unique colors: {len(colors)}")

#CALCULATE GRID SIZE
# Okay, so, to explain this\/ we have a set number of colors, say, 20.
# We need to arrange those in a grid. If we conveniently had, say,
# 16 colors, we could have a perfect grid of 4x4 colors, but we dont,
# so instead we round up to 5x5 color slots. They wont all be used, as
# now we have 25 spaces out of our 21 colors, but thats the best we can
# do. So 5 rows, allocate 16x16 pixels for each color slot, that turns
# out to a total of 40x40 pixels, but we want to use texture sizes that
# are powers of 2 (memory usage n all that), so we round up to 64x64.
# Thank you for coming to my ted talk.
#PROGRESS_UPDATE--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/
update_progress(filepath, 36, "Calculating Grid Size")

color_count = len(colors)
grid_size = math.ceil(math.sqrt(color_count))
texture_size = grid_size * 8

texture_size = 2 ** math.ceil(math.log2(texture_size))

print(f"texture size: {texture_size}x{texture_size}")

#MAKE BAKE IMAGE
bake_image = bpy.data.images.new("BakeTexture", width=texture_size, height=texture_size)

#ADD IMAGE TEXTURE NODE TO EVERY MATERIAL
#PROGRESS_UPDATE--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/
update_progress(filepath, 42, "Applying Bake Texture")

for mat in obj.data.materials:
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    #REMOVE ANY EXISTING TEXTURE NODES
    
    for node in list(nodes):
        if node.type == 'TEX_IMAGE':
            nodes.remove(node)
    
    #GET BDSF CURRENT BASE COLOR
    bsdf = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
    color = bsdf.inputs['Base Color'].default_value[:]
    
    #CREATE AND LINK RGB TEXTURE NODE
    rgb_node = nodes.new("ShaderNodeRGB")
    rgb_node.outputs[0].default_value = color
    links.new(rgb_node.outputs[0], bsdf.inputs['Base Color'])
    
    #ADD IMAGE TEXTURE NODE

    for node in nodes:
        node.select = False
    tex_node = nodes.new("ShaderNodeTexImage")
    tex_node.image = bake_image
    tex_node.select = True
    nodes.active = tex_node


# /////////// PREPARE UV'S /////////// #
#PROGRESS_UPDATE--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/
update_progress(filepath, 48, "Initializing Shading Setup")
 #PROGRESS_UPDATE--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/
update_progress(filepath, 54, "Creating Texture Node")
#PROGRESS_UPDATE--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/
update_progress(filepath, 60, "Preparing UV's")

#ENSURE WE HAVE A UV MAP
if not obj.data.uv_layers:
    obj.data.uv_layers.new(name="UVMap")

#LOOP THROUGH AND SET THE UV POSITION FOR EACH MATERIAL
#PROGRESS_UPDATE--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/
update_progress(filepath, 66, "Calculating Vertex Coordinates")

bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='DESELECT')

bpy.ops.object.mode_set(mode='EDIT')

slot_size = 8 / texture_size

bm = bmesh.from_edit_mesh(obj.data)
uv_layer = bm.loops.layers.uv.active

for i in range(len(obj.data.materials)):
    col = i % grid_size
    row = i // grid_size
    center_u = (col + 0.5) * slot_size
    center_v = (row + 0.5) * slot_size

    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.context.object.active_material_index = i
    bpy.ops.object.material_slot_select()
    
    for fi, face in enumerate(bm.faces):
        if face.select:
            for j, loop in enumerate(face.loops):
                angle = (2 * math.pi * j) / len(face.loops)
                radius = 1 / texture_size
                u = center_u + radius * math.cos(angle)
                v = center_v + radius * math.sin(angle)
                loop[uv_layer].uv = (u, v)

bmesh.update_edit_mesh(obj.data)

bpy.ops.object.mode_set(mode='OBJECT')

# /////////// BAKE /////////// #
#PROGRESS_UPDATE--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/
update_progress(filepath, 72, "Initializing Bake")

#PREPARE BAKE
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.bake_type = 'DIFFUSE'
bpy.context.scene.render.bake.use_pass_direct = False
bpy.context.scene.render.bake.use_pass_indirect = False
bpy.context.scene.render.bake.margin = 10
bpy.context.scene.cycles.samples = 1
bpy.context.scene.render.filter_size = 0.01


#BAKE
#PROGRESS_UPDATE--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/
update_progress(filepath, 78, "Baking")

bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, save_mode='INTERNAL')
print(f"has data: {bake_image.has_data}")

# /////////// SAVE TO DISK /////////// #
#PROGRESS_UPDATE--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/
update_progress(filepath, 84, "Exporting Texture Image")

output_dir = argv[1]

output_path = os.path.join(output_dir, os.path.basename(filepath).replace(".obj", "_baked.png"))
print(f"saving to: {output_path}")
bake_image.filepath_raw = output_path
bake_image.file_format = 'PNG'
bake_image.save()

#PROGRESS_UPDATE--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/
update_progress(filepath, 90, "Exporting Joined Mesh")

output_fbx_path = os.path.join(output_dir, os.path.basename(filepath).replace(".obj", "_baked.fbx"))
bpy.ops.export_scene.fbx(filepath=output_fbx_path, global_scale=0.01)

#PROGRESS_UPDATE--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/--/
update_progress(filepath, 100, "Done!")

print(f"saved to {output_path}")