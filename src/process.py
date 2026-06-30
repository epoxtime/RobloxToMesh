###############################
# THIS CODE IS RAN IN BLENDER #
###############################

# Ignore warnings
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
    time.sleep(0.001)

# /////////// PREPARE OBJECT /////////// #

#DELETE ALL OBJECTS AND MATERIALS
update_progress(filepath, 1, "Initializing")

bpy.ops.object.select_all(action='SELECT')
update_progress(filepath, 2, "Clearing Scene Objects")
bpy.ops.object.delete()

update_progress(filepath, 3, "Clearing Materials")
for mat in list(bpy.data.materials):
    bpy.data.materials.remove(mat)

#IMPORT THE MESH
update_progress(filepath, 4, "Importing Mesh")

bpy.ops.wm.obj_import(filepath=filepath)

update_progress(filepath, 5, "Mesh Imported")
print(bpy.context.selected_objects)

update_progress(filepath, 6, "Joining Imported Objects")
bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
bpy.ops.object.join()

update_progress(filepath, 7, "Centering Object")
bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
bpy.ops.object.location_clear()

#REMOVE STUD MATERIALS (ROBLOX ADDS A "_diff" MATERIAL TO EVERY PART, WE DONT WANT IT)
update_progress(filepath, 8, "Removing Stud Materials")
for o in bpy.context.scene.objects:
    if o.type != 'MESH':
        continue
    for slot_index in reversed(range(len(o.data.materials))):
        mat = o.data.materials[slot_index]
        if mat and mat.name.endswith("_diff"):
            o.data.materials.pop(index=slot_index)

# /////////// OPTIMIZE GEOMETRY /////////// #
update_progress(filepath, 9, "Optimizing Geometry")

# SEPARATE BY LOOSE PARTS
update_progress(filepath, 10, "Entering Edit Mode")
bpy.ops.object.mode_set(mode='EDIT')
update_progress(filepath, 11, "Separating Loose Parts")
bpy.ops.mesh.separate(type='LOOSE')
bpy.ops.object.mode_set(mode='OBJECT')

# GROUP BY MATERIAL
update_progress(filepath, 12, "Grouping By Material")
material_groups = {}
for o in bpy.context.scene.objects:
    if o.type != 'MESH':
        continue
    used_mats = set(f.material_index for f in o.data.polygons)
    if not used_mats:
        continue
    mat = o.data.materials[list(used_mats)[0]]
    if mat not in material_groups:
        material_groups[mat] = []
    material_groups[mat].append(o)

    print(f"unique material groups: {len(material_groups)}")
    for mat, objects in material_groups.items():
        print(f"  {mat.name}: {len(objects)} objects")

# BOOLEAN UNION PER MATERIAL USING COLLECTIONS
update_progress(filepath, 14, "Merging Meshes By Material")
result_objects = []
total_groups = len(material_groups)
for gi, (mat, objects) in enumerate(material_groups.items()):
    update_progress(filepath, 14 + int((gi / max(total_groups, 1)) * 6), f"Merging Material {gi + 1}/{total_groups}")

    for o in objects:
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = o
        o.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=0.0001)
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.mesh.delete_loose()
        bpy.ops.object.mode_set(mode='OBJECT')
        o.select_set(False)

    base = objects[0]

    if len(objects) > 1:
        col = bpy.data.collections.new(mat.name)
        bpy.context.scene.collection.children.link(col)

        # add all objects EXCEPT base to the collection
        for o in objects[1:]:
            col.objects.link(o)

        mod = base.modifiers.new(name="Boolean", type='BOOLEAN')
        mod.operation = 'UNION'
        mod.solver = 'EXACT'
        mod.collection = col
        mod.operand_type = 'COLLECTION'
        bpy.context.view_layer.objects.active = base
        bpy.ops.object.modifier_apply(modifier=mod.name)

        for o in objects[1:]:
            bpy.data.objects.remove(o)
        bpy.data.collections.remove(col)

    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = base
    base.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    base.select_set(False)

    result_objects.append(base)

# CLEAN UP EACH OBJECT
update_progress(filepath, 20, "Cleaning Up Geometry")
total_results = len(result_objects)
for ri, o in enumerate(result_objects):
    update_progress(filepath, 20 + int((ri / max(total_results, 1)) * 6), f"Cleaning Object {ri + 1}/{total_results}")
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.0001)
    bpy.ops.mesh.dissolve_limited(angle_limit=math.radians(0.1))
    bpy.ops.mesh.quads_convert_to_tris()
    bpy.ops.object.mode_set(mode='OBJECT')
    o.select_set(False)

# JOIN ALL BACK INTO ONE
update_progress(filepath, 26, "Joining Meshes")
bpy.ops.object.select_all(action='DESELECT')
for o in result_objects:
    o.select_set(True)
bpy.context.view_layer.objects.active = result_objects[0]
bpy.ops.object.join()
obj = bpy.context.active_object

update_progress(filepath, 27, "Shading Flat")
bpy.ops.object.shade_flat()

update_progress(filepath, 28, "Clearing Custom Split Normals")
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.customdata_custom_splitnormals_clear()
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.shade_flat()

# /////////// PREPARE TEXTURE /////////// #
update_progress(filepath, 29, "Preparing Texture")

#FIND TOTAL NUMBER OF UNIQE COLORS. DONT WASTE TEXTURE SPACE ON DUPLICATES
update_progress(filepath, 30, "Collecting Unique Colors")
colors = set()
for mat in obj.data.materials:
    c = mat.diffuse_color
    rounded = tuple(round(v, 2) for v in c[:3])
    colors.add(rounded)

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
update_progress(filepath, 31, "Calculating Grid Size")

color_count = len(obj.data.materials)
grid_size = math.ceil(math.sqrt(color_count))
texture_size = grid_size * 8

update_progress(filepath, 32, "Rounding To Power Of Two")
texture_size = 2 ** math.ceil(math.log2(texture_size))

print(f"texture size: {texture_size}x{texture_size}")

#MAKE BAKE IMAGE
update_progress(filepath, 33, "Creating Bake Image")
bake_image = bpy.data.images.new("BakeTexture", width=texture_size, height=texture_size)

#ADD IMAGE TEXTURE NODE TO EVERY MATERIAL
update_progress(filepath, 34, "Applying Bake Texture")

total_mats = len(obj.data.materials)
for mi, mat in enumerate(obj.data.materials):
    update_progress(filepath, 34 + int((mi / max(total_mats, 1)) * 10), f"Setting Up Material {mi + 1}/{total_mats}")
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
update_progress(filepath, 44, "Initializing Shading Setup")
update_progress(filepath, 45, "Preparing UV's")

#ENSURE WE HAVE A UV MAP
update_progress(filepath, 46, "Ensuring UV Map Exists")
if not obj.data.uv_layers:
    obj.data.uv_layers.new(name="UVMap")

#LOOP THROUGH AND SET THE UV POSITION FOR EACH MATERIAL
update_progress(filepath, 47, "Calculating Vertex Coordinates")

slot_px = 8  # pixels per color slot

bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='DESELECT')

bpy.ops.object.mode_set(mode='EDIT')

slot_size = slot_px / texture_size

bm = bmesh.from_edit_mesh(obj.data)
uv_layer = bm.loops.layers.uv.active

update_progress(filepath, 48, "Assigning Bake UV's")
for i in range(len(obj.data.materials)):
    update_progress(filepath, 48 + int((i / max(len(obj.data.materials), 1)) * 12), f"Bake UV Slot {i + 1}/{len(obj.data.materials)}")
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

update_progress(filepath, 60, "Updating Mesh UV's")
bmesh.update_edit_mesh(obj.data)

bpy.ops.object.mode_set(mode='OBJECT')

# /////////// BAKE /////////// #
update_progress(filepath, 61, "Initializing Bake")

#PREPARE BAKE
update_progress(filepath, 62, "Setting Render Engine To Cycles")
bpy.context.scene.render.engine = 'CYCLES'
update_progress(filepath, 63, "Configuring Bake Settings")
bpy.context.scene.cycles.bake_type = 'DIFFUSE'
bpy.context.scene.render.bake.use_pass_direct = False
bpy.context.scene.render.bake.use_pass_indirect = False
bpy.context.scene.render.bake.margin = 2
bpy.context.scene.cycles.samples = 1
bpy.context.scene.render.filter_size = 0.01

#BAKE
update_progress(filepath, 64, "Baking")

bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, save_mode='INTERNAL')
update_progress(filepath, 72, "Bake Complete")
print(f"has data: {bake_image.has_data}")

# /////////// CENTER VERTS AFTER BAKE /////////// #
update_progress(filepath, 73, "Centering Verts After Bake")

bpy.ops.object.mode_set(mode='EDIT')
bm = bmesh.from_edit_mesh(obj.data)
uv_layer = bm.loops.layers.uv.active

bpy.ops.object.mode_set(mode='EDIT')

for i in range(len(obj.data.materials)):
    update_progress(filepath, 73 + int((i / max(len(obj.data.materials), 1)) * 4), f"Centering UV Slot {i + 1}/{len(obj.data.materials)}")
    col = i % grid_size
    row = i // grid_size
    center_u = (col + 0.5) * slot_size
    center_v = (row + 0.5) * slot_size

    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.context.object.active_material_index = i
    bpy.ops.object.material_slot_select()

    for face in bm.faces:
        if face.select:
            for loop in face.loops:
                loop[uv_layer].uv = (center_u, center_v)

update_progress(filepath, 77, "Updating Centered UV's")
bmesh.update_edit_mesh(obj.data)
bpy.ops.object.mode_set(mode='OBJECT')

# /////////// OPTIMIZE FILE /////////// #
# tldr; we need a larger file to bake the texture, and all we're really doing
# is getting the color for the specific verts. So we only *really* need one
# pixel per color. So that's what we'll do. Make a new image, with code this
# time, that has one pixel per color, setting the vertex positions to that pixel.

#FIND COLORS
update_progress(filepath, 78, "Sampling Baked Colors")

sampled_colors = []

pixels_data = list(bake_image.pixels)

print("MATERIALS:", len(obj.data.materials))
print("UNIQUE COLORS:", len(colors))
print("GRID SIZE:", grid_size, "TEXTURE SIZE:", texture_size)

for i in range(len(obj.data.materials)):
    update_progress(filepath, 78 + int((i / max(len(obj.data.materials), 1)) * 2), f"Sampling Color {i + 1}/{len(obj.data.materials)}")
    col = i % grid_size
    row = i // grid_size
    center_u = (col + 0.5) * slot_size
    center_v = (row + 0.5) * slot_size
    
    x = int(center_u * texture_size)
    y = int(center_v * texture_size)
    index = (y * texture_size + x) * 4

    r, g, b, a = pixels_data[index:index+4]
    sampled_colors.append((r, g, b, a))

#MAKE NEW IMAGE
update_progress(filepath, 80, "Creating Final Image")
final_size = texture_size  # same size as bake texture
final_image = bpy.data.images.new("FinalTexture", width=final_size, height=final_size)
final_image.colorspace_settings.name = 'Non-Color'

update_progress(filepath, 81, "Writing Final Pixels")
pixels = [0.0] * (final_size * final_size * 4)

for i, (r, g, b, a) in enumerate(sampled_colors):
    col = i % grid_size
    row = i // grid_size
    
    # fill 8x8 block
    for py in range(1, 7):
        for px in range(1 ,7):
            x = col * slot_px + px
            y = row * slot_px + py
            index = (y * final_size + x) * 4
            pixels[index] = r
            pixels[index + 1] = g
            pixels[index + 2] = b
            pixels[index + 3] = 1.0

update_progress(filepath, 82, "Applying Final Pixels")
final_image.pixels = pixels

#REMAP UV's
update_progress(filepath, 83, "Remapping Final UV's")
bpy.ops.object.mode_set(mode='EDIT')
bm = bmesh.from_edit_mesh(obj.data)
uv_layer = bm.loops.layers.uv.active

for i in range(len(obj.data.materials)):
    col = i % grid_size
    row = i // grid_size
    
    u = (col * slot_px + 4) / final_size
    v = (row * slot_px + 4) / final_size

    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.context.object.active_material_index = i
    bpy.ops.object.material_slot_select()

    for face in bm.faces:
        if face.select:
            for loop in face.loops:
                loop[uv_layer].uv = (u, v)

bmesh.update_edit_mesh(obj.data)
bpy.ops.object.mode_set(mode='OBJECT')

# /////////// SAVE TO DISK /////////// #
update_progress(filepath, 84, "Exporting Texture Image")

output_dir = argv[1]

output_path = os.path.join(output_dir, os.path.basename(filepath).replace(".obj", "_baked.png"))
print(f"saving to: {output_path}")
final_image.filepath_raw = output_path
final_image.file_format = 'PNG'

update_progress(filepath, 88, "Saving Texture To Disk")
final_image.save()

update_progress(filepath, 90, "Exporting Joined Mesh")

output_fbx_path = os.path.join(output_dir, os.path.basename(filepath).replace(".obj", "_baked.fbx"))
update_progress(filepath, 95, "Writing FBX File")
bpy.ops.export_scene.fbx(filepath=output_fbx_path, global_scale=0.01)

update_progress(filepath, 100, "Done!")

print(f"saved to {output_path}")