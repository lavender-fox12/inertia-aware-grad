#READ THIS!!
# You'll need to install VPython: pip install vpython
# Then run from VS Code: python tribomagnetic_memory_demo.py
# This will open a tab thats in your browser with the visualization.

from vpython import *
import numpy as np
import random

# --- Simulation Parameters ---
FILM_WIDTH = 200e-9  # meters (ex. 200 nm wide strip for visualization)
FILM_LENGTH = 1000e-9 # meters (1 um long)
FILM_THICKNESS = 30e-9 # CoFeB film thickness
SUBSTRATE_THICKNESS = 50e-9
SPACER_THICKNESS = 5e-9 # Al2O3 spacer

DOMAIN_SIZE = 25e-9 # meters (target domain pitch)
NUM_DOMAINS_X = int(FILM_WIDTH / DOMAIN_SIZE)
NUM_DOMAINS_Y = int(FILM_LENGTH / DOMAIN_SIZE)

SAW_FREQ_VISUAL = 62.5e6 # Hz (for visual timing, not true physics speed)
SAW_AMPLITUDE_STRAIN_BASE = 0.001 # Arbitrary base strain for visual effect
SAW_AMPLITUDE_TRIBO_CHARGE_VISUAL = 0.0005 # Arbitrary visual for charge

# Magnetization parameters
INITIAL_MAGNETIZATION_ANGLE_DEG = 0 # Degrees, relative to y-axis (long axis of film)
MAX_ROTATION_STRAIN_DEG = 15 # Max rotation due to pure magnetoelastic effect
TRIBO_ENHANCEMENT_FACTOR = 1.4 # 40% enhancement
MAX_ROTATION_TRIBO_DEG = MAX_ROTATION_STRAIN_DEG * TRIBO_ENHANCEMENT_FACTOR # Max rotation with tribo

# Retention parameters (scaled for demo time)
RETENTION_TIME_STRAIN_S = 2.0 # Seconds (representing 2-5 minutes)
RETENTION_TIME_TRIBO_S = 6.0  # Seconds (representing ~15 minutes) -> 3x longer

# Colors
COLOR_FILM = color.gray(0.6)
COLOR_SUBSTRATE = color.cyan
COLOR_SPACER = color.white
COLOR_DOMAIN_UP = color.red
COLOR_DOMAIN_DOWN = color.blue
COLOR_SAW_HIGHLIGHT = color.yellow
COLOR_TRIBO_CHARGE = color.orange

# --- Scene Setup ---
scene.width = 1000
scene.height = 700
scene.title = "Tribomagnetic Memory: Acoustic Modulation of Magnetic Domains via Triboelectric Coupling"
scene.caption = "Toggle SAW and Triboelectric Effect. Observe domain rotation and retention."
scene.camera.pos = vector(FILM_WIDTH*0.5, FILM_LENGTH*0.5, FILM_LENGTH*2.5)
scene.camera.axis = -scene.camera.pos + vector(FILM_WIDTH*0.5, FILM_LENGTH*0.1, 0)

# MODIFIED LIGHTS SETUP:
# scene.lights = [distant_light(direction=vector(0.2,0.2,-1)), distant_light(direction=vector(-0.2,-0.2,1))] # OLD WAY

# NEW WAY:
# 1. Optionally, remove default lights if you want only your custom ones
scene.lights = [] # This clears any default lighting
# 2. Create your new lights. They are automatically added to the scene.
distant_light(direction=vector(0.2, 0.2, -1), color=color.gray(0.8)) # A primary light source
distant_light(direction=vector(-0.2, -0.2, 1), color=color.gray(0.4)) # A secondary/fill light


# --- Create Visual Objects ---

# Substrate (PMN-PT)
substrate = box(pos=vector(FILM_WIDTH/2, -FILM_THICKNESS/2 - SPACER_THICKNESS - SUBSTRATE_THICKNESS/2, FILM_LENGTH/2),
                size=vector(FILM_WIDTH, SUBSTRATE_THICKNESS, FILM_LENGTH),
                color=COLOR_SUBSTRATE, opacity=0.7)
substrate_label = label(pos=substrate.pos - vector(0, SUBSTRATE_THICKNESS,0), text="PMN-PT Substrate", xoffset=0, yoffset=-30, space=10, height=12, border=4, font='sans')


# Al2O3 Spacer Layer
spacer = box(pos=vector(FILM_WIDTH/2, -FILM_THICKNESS/2 - SPACER_THICKNESS/2, FILM_LENGTH/2),
             size=vector(FILM_WIDTH, SPACER_THICKNESS, FILM_LENGTH),
             color=COLOR_SPACER, opacity=0.8)
spacer_label = label(pos=spacer.pos, text="Al2O3 Spacer", xoffset=0, yoffset=-10, space=10, height=12, border=4, font='sans')


# Ferromagnetic Film (CoFeB)
film = box(pos=vector(FILM_WIDTH/2, 0, FILM_LENGTH/2),
           size=vector(FILM_WIDTH, FILM_THICKNESS, FILM_LENGTH),
           color=COLOR_FILM, opacity=0.3) # Make it somewhat transparent to see domains
film_label = label(pos=film.pos + vector(0, FILM_THICKNESS,0), text="CoFeB Film", xoffset=0, yoffset=20, space=10, height=12, border=4, font='sans')


# Magnetic Domains (represented by arrows)
domains = []
domain_states = [] # Store [current_angle_rad, target_angle_rad, retention_timer, original_angle_rad]

for i in range(NUM_DOMAINS_X):
    for j in range(NUM_DOMAINS_Y):
        x = (i + 0.5) * DOMAIN_SIZE
        y_pos = (j + 0.5) * DOMAIN_SIZE # Position along length of film
        
        # Initial slight random perturbation for visual interest
        initial_angle_rad = np.radians(INITIAL_MAGNETIZATION_ANGLE_DEG + random.uniform(-5,5))
        
        # Represent domains as arrows. Length proportional to DOMAIN_SIZE.
        # Arrow points along y-axis initially (or initial_angle_rad)
        domain_arrow = arrow(
            pos=vector(x, 0, y_pos), # Centered on the film's mid-plane
            axis=vector(0, DOMAIN_SIZE * 0.8 * np.cos(initial_angle_rad), DOMAIN_SIZE * 0.8 * np.sin(initial_angle_rad)), # Pointing along y
            shaftwidth=FILM_THICKNESS * 2,
            headwidth=FILM_THICKNESS * 3,
            headlength=FILM_THICKNESS * 1.5,
            color=COLOR_DOMAIN_UP if np.cos(initial_angle_rad) > 0 else COLOR_DOMAIN_DOWN
        )
        domains.append(domain_arrow)
        domain_states.append({'current_angle_rad': initial_angle_rad, 
                              'target_angle_rad': initial_angle_rad, 
                              'retention_timer': 0.0,
                              'original_angle_rad': initial_angle_rad,
                              'is_flipped': False,
                              'max_rotation_rad': 0.0 # Max rotation it experienced
                             })

# SAW visualizer (a transparent ripple)
saw_visual_width = FILM_WIDTH
saw_visual_thickness = DOMAIN_SIZE # Thickness of the wave packet
saw_visual = box(pos=vector(FILM_WIDTH/2, 0, -saw_visual_thickness/2), # Starts at one end
                 size=vector(saw_visual_width, FILM_THICKNESS*1.5, saw_visual_thickness),
                 color=COLOR_SAW_HIGHLIGHT, opacity=0.4, visible=False)

# Triboelectric charge visualizer (subtle glow under SAW)
tribo_charge_visual = box(pos=vector(FILM_WIDTH/2, -SPACER_THICKNESS/4, -saw_visual_thickness/2),
                          size=vector(saw_visual_width, SPACER_THICKNESS*0.5, saw_visual_thickness),
                          color=COLOR_TRIBO_CHARGE, opacity=0.7, emissive=True, visible=False)


# --- UI Controls ---
saw_on = False
tribo_on = False

def toggle_saw():
    global saw_on, saw_visual_y_pos # saw_visual_y_pos was not global, added it
    saw_on = not saw_on
    if saw_on:
        saw_button.text = "SAW: ON (Click to Stop)"
        saw_visual.pos.z = -saw_visual_thickness/2 # Reset SAW position
        saw_visual.visible = True
        if tribo_on: tribo_charge_visual.visible = True
    else:
        saw_button.text = "SAW: OFF (Click to Start)"
        saw_visual.visible = False
        tribo_charge_visual.visible = False
    update_digital_twin_text()

def toggle_tribo():
    global tribo_on
    tribo_on = not tribo_on
    if tribo_on:
        tribo_button.text = "Triboelectric Boost: ON"
        if saw_on: tribo_charge_visual.visible = True
    else:
        tribo_button.text = "Triboelectric Boost: OFF"
        tribo_charge_visual.visible = False
    update_digital_twin_text()

scene.append_to_caption('\n')
saw_button = button(bind=toggle_saw, text="SAW: OFF (Click to Start)")
scene.append_to_caption('  ')
tribo_button = button(bind=toggle_tribo, text="Triboelectric Boost: OFF")
scene.append_to_caption('\n\n')

# --- Digital Twin Display ---
digital_twin_text = wtext(text="Initializing Digital Twin...")
def update_digital_twin_text():
    max_rot_deg = MAX_ROTATION_TRIBO_DEG if tribo_on else MAX_ROTATION_STRAIN_DEG
    ret_time_s = RETENTION_TIME_TRIBO_S if tribo_on else RETENTION_TIME_STRAIN_S
    
    avg_rotation_perc = 0
    active_domains = 0
    for i, state in enumerate(domain_states):
        if state['is_flipped']: 
            angle_diff = abs(state['current_angle_rad'] - state['original_angle_rad'])
            # Use the stored max_rotation_rad for this specific flip event
            max_possible_rot_this_flip = abs(state['max_rotation_rad'] - state['original_angle_rad'])
            if max_possible_rot_this_flip > np.radians(1): # Ensure meaningful rotation
                 avg_rotation_perc += (angle_diff / max_possible_rot_this_flip) * 100
                 active_domains +=1
    if active_domains > 0:
        avg_rotation_perc /= active_domains
    else:
        avg_rotation_perc = 0


    base_nT = 10 
    max_nT_strain = 30 
    max_nT_tribo = 50 
    
    current_max_nT = max_nT_tribo if tribo_on else max_nT_strain
    # Scale simulated_delta_B_nT based on how much of the *potential* rotation (for current mode) is achieved
    simulated_delta_B_nT = base_nT + (current_max_nT - base_nT) * (avg_rotation_perc / 100.0)
    simulated_delta_B_nT = max(base_nT, min(simulated_delta_B_nT, current_max_nT)) # Clamp to range


    text_content = f"""--- DIGITAL TWIN MONITOR ---
<b>Research Parameters:</b>
  SAW Freq: {SAW_FREQ_VISUAL/1e6:.1f} MHz (visual)
  Magnetoelastic Δθ: {MAX_ROTATION_STRAIN_DEG}°
  Tribo-Enhanced Δθ: {MAX_ROTATION_TRIBO_DEG}° (+{((TRIBO_ENHANCEMENT_FACTOR-1)*100):.0f}%)
  Base Retention (τ_strain): {RETENTION_TIME_STRAIN_S*1000:.0f} ms (demo scale)
  Tribo Retention (τ_tribo): {RETENTION_TIME_TRIBO_S*1000:.0f} ms (demo scale)
  Predicted Max ΔB (Strain): ~{max_nT_strain} nT
  Predicted Max ΔB (Tribo): ~{max_nT_tribo} nT

<b>Current Simulation State:</b>
  SAW Status: {'PROPAGATING' if saw_on else 'IDLE'}
  Triboelectric Coupling: {'<b>ACTIVE</b>' if tribo_on else 'INACTIVE'}
  Expected Max Domain Rotation: {max_rot_deg:.1f}°
  Expected Retention Time (τ): {ret_time_s:.1f} s (demo scale)
  Simulated Avg. Domain Flipped State: {avg_rotation_perc:.1f}% of max potential rotation
  <b>Estimated ΔB Field (Simulation): {simulated_delta_B_nT:.1f} nT</b>
"""
    digital_twin_text.text = text_content

update_digital_twin_text()


# --- Animation Loop ---
dt = 0.01 # Timestep for animation
saw_speed = FILM_LENGTH / 5.0 # SAW traverses film in 5 seconds (adjust for visual preference)
saw_visual_y_pos = -saw_visual_thickness/2 # Initialize this variable here

while True:
    rate(100) # Max 100 updates per second

    if saw_on:
        # Move SAW
        saw_visual_y_pos += saw_speed * dt # saw_visual_y_pos was used here before being global/initialized properly
        saw_visual.pos.z = saw_visual_y_pos
        if tribo_on:
            tribo_charge_visual.pos.z = saw_visual_y_pos
            tribo_charge_visual.visible = True
        else:
            tribo_charge_visual.visible = False
        
        if saw_visual_y_pos > FILM_LENGTH + saw_visual_thickness/2:
            saw_visual_y_pos = -saw_visual_thickness/2 # Reset SAW
            # Optionally turn off SAW after one pass:
            # toggle_saw() 

        # Interact with domains
        for i, domain in enumerate(domains):
            state = domain_states[i]
            # Check if SAW is over this domain
            if domain.pos.z - DOMAIN_SIZE/2 < saw_visual.pos.z + saw_visual.size.z/2 and \
               domain.pos.z + DOMAIN_SIZE/2 > saw_visual.pos.z - saw_visual.size.z/2:
                
                if not state['is_flipped']: 
                    state['is_flipped'] = True
                    
                    max_rotation_this_flip_deg = MAX_ROTATION_TRIBO_DEG if tribo_on else MAX_ROTATION_STRAIN_DEG
                    
                    # Determine flip direction. Let's make it flip towards a significant angle.
                    # If current angle is positive, flip towards negative max, if negative, flip towards positive max.
                    # This makes the "bit flip" more visually obvious.
                    if np.cos(state['original_angle_rad']) >= 0: # Initially "up-ish"
                        state['target_angle_rad'] = state['original_angle_rad'] - np.radians(max_rotation_this_flip_deg)
                    else: # Initially "down-ish"
                        state['target_angle_rad'] = state['original_angle_rad'] + np.radians(max_rotation_this_flip_deg)
                    
                    # Ensure target angle is within reasonable bounds (e.g., -pi to pi from original, or -180 to 180 deg)
                    # This is a simple clamping, could be more sophisticated
                    state['target_angle_rad'] = np.arctan2(np.sin(state['target_angle_rad']), np.cos(state['target_angle_rad']))


                    state['max_rotation_rad'] = state['target_angle_rad'] 
                    state['retention_timer'] = RETENTION_TIME_TRIBO_S if tribo_on else RETENTION_TIME_STRAIN_S
                    

    # Handle domain rotation and retention
    any_domain_active = False
    for i, domain in enumerate(domains):
        state = domain_states[i]

        if state['is_flipped'] and abs(state['current_angle_rad'] - state['target_angle_rad']) > np.radians(0.5): # Target small threshold
            angle_diff = state['target_angle_rad'] - state['current_angle_rad']
            # Normalize angle_diff to be between -pi and pi for smoother rotation
            angle_diff = np.arctan2(np.sin(angle_diff), np.cos(angle_diff))
            state['current_angle_rad'] += angle_diff * 0.2 
            state['current_angle_rad'] = np.arctan2(np.sin(state['current_angle_rad']), np.cos(state['current_angle_rad'])) # Normalize
            any_domain_active = True

        if state['is_flipped'] and state['retention_timer'] > 0:
            state['retention_timer'] -= dt
            if state['retention_timer'] <= 0:
                state['retention_timer'] = 0
                state['target_angle_rad'] = state['original_angle_rad'] 
            any_domain_active = True

        elif state['is_flipped'] and state['retention_timer'] <= 0: 
            if abs(state['current_angle_rad'] - state['original_angle_rad']) > np.radians(0.5):
                angle_diff = state['original_angle_rad'] - state['current_angle_rad']
                angle_diff = np.arctan2(np.sin(angle_diff), np.cos(angle_diff)) # Normalize
                state['current_angle_rad'] += angle_diff * 0.05 
                state['current_angle_rad'] = np.arctan2(np.sin(state['current_angle_rad']), np.cos(state['current_angle_rad'])) # Normalize
                any_domain_active = True
            else:
                state['current_angle_rad'] = state['original_angle_rad'] 
                state['is_flipped'] = False 
                state['max_rotation_rad'] = 0.0 
        
        new_axis_y = DOMAIN_SIZE * 0.8 * np.cos(state['current_angle_rad'])
        new_axis_z = DOMAIN_SIZE * 0.8 * np.sin(state['current_angle_rad']) # This was likely intended to be sin for rotation in YZ plane
        domain.axis = vector(0, new_axis_y, new_axis_z) 

        domain.color = COLOR_DOMAIN_UP if np.cos(state['current_angle_rad']) > 0.1 else \
                       (COLOR_DOMAIN_DOWN if np.cos(state['current_angle_rad']) < -0.1 else color.gray(0.5))


    if any_domain_active or saw_on : 
        update_digital_twin_text()