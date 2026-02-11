# Example Interactive Installation

[![ORGAN-II: Poiesis](https://img.shields.io/badge/ORGAN--II-Poiesis-6a1b9a?style=flat-square)](https://github.com/organvm-ii-poiesis)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)
[![Status](https://img.shields.io/badge/status-active--development-yellow?style=flat-square)]()

> A reference implementation for sensor-driven interactive art installations -- from depth cameras and LIDAR to real-time audio-visual response, with a complete exhibition deployment guide for gallery and museum contexts.

[Artistic Purpose](#artistic-purpose) | [Conceptual Approach](#conceptual-approach) | [Technical Overview](#technical-overview) | [Installation](#installation) | [Quick Start](#quick-start) | [Working Examples](#working-examples) | [Theory Implemented](#theory-implemented) | [Portfolio & Exhibition](#portfolio--exhibition) | [Related Work](#related-work) | [Contributing](#contributing) | [License & Author](#license--author)

---

## Artistic Purpose

An interactive installation is not software that happens to be in a room. It is a room that happens to contain software. This distinction determines everything: how you design, how you test, how you deploy, how you maintain, and how you document. The primary medium is not the screen or the projection or the sound -- it is the space itself and the bodies that move through it. The software serves the spatial experience. When the software fails, the room goes dark, the sound stops, and a gallery full of visitors stares at a dead screen. When the software succeeds, visitors forget there is software at all. They are inside something.

Example Interactive Installation is a reference implementation for building sensor-driven interactive art that responds to participant presence and movement in real time. It provides the complete technical blueprint -- from hardware selection through sensor calibration to failsafe protocols -- that an artist needs to take a concept from studio prototype to exhibition-ready deployment. The repository is not a finished artwork. It is the infrastructure on which finished artworks are built: a documented, tested, extensible system for detecting human bodies in space and translating their positions, gestures, velocities, and proximities into audio-visual responses at sub-frame latency.

The project exists because the knowledge needed to deploy interactive installations in professional exhibition contexts is tribal. It lives in the heads of technical directors at media art studios, in the institutional memory of museums that have hosted interactive work, in the hard-won experience of artists who have watched their pieces fail on opening night because they did not account for ambient infrared from the gallery's skylights, or because the depth camera's field of view did not cover the corner where visitors tend to congregate, or because the failover routine did not handle the specific way that a LIDAR unit reports connection loss. These failures are preventable. They are preventable through documentation, through reference implementations, through checklists written by people who have already made the mistakes. This repository is that documentation.

It is built on [metasystem-master](https://github.com/organvm-ii-poiesis/metasystem-master)'s performance-sdk, inheriting the Omni-Dromenon Engine's consensus algorithms and real-time parameter bus. But where metasystem-master is a general-purpose performance engine, this repository is a specific application: an installation that uses depth cameras, LIDAR, and capacitive touch surfaces to detect participants and generate responsive audiovisual environments. It is opinionated about hardware, specific about calibration procedures, and exhaustive about failure modes. It is the repository you read before you buy the equipment, not after.

---

## Conceptual Approach

### The Body as Input Device

Interactive installations that reduce human bodies to cursor positions -- "stand here to trigger this" -- miss the richness of embodied experience. A body is not a point in space. It has volume, velocity, orientation, gesture, warmth, breath. The conceptual foundation of this installation is that the sensing system should capture as much of this richness as is technically feasible, and the response system should use it to create experiences that feel embodied rather than triggered.

The sensing pipeline extracts multiple features from each detected body:

| Feature | Sensor | Update Rate | Precision |
|---------|--------|-------------|-----------|
| Position (x, y, z) | Depth camera + LIDAR | 30 Hz | +/- 2 cm |
| Velocity vector | Computed from position delta | 30 Hz | Smoothed over 5 frames |
| Body orientation | Depth camera skeleton tracking | 30 Hz | +/- 15 degrees |
| Gesture class | ML model on depth data | 15 Hz | 12 gesture classes |
| Proximity to surfaces | LIDAR point cloud | 20 Hz | +/- 1 cm |
| Touch pressure | Capacitive surface array | 60 Hz | 256 pressure levels |
| Group density | Computed from all positions | 10 Hz | Persons per sq. meter |

Each of these features feeds into the response engine as a continuous parameter, not a discrete trigger. A person walking slowly toward a projection surface does not "trigger" a visual change at a threshold distance -- the visuals continuously respond to their approach, creating a gradient of intimacy between the participant and the artwork. A group of three people standing close together produces a different response than three people spread across the room, because group density modulates the audio spatialization and visual complexity parameters. The installation reads the room, not individual button presses.

### Spatial Composition

An installation must be designed for a specific spatial configuration, but the code should be adaptable to different spaces. This repository uses a spatial configuration model that separates the abstract behavior (what should happen when a body approaches a surface) from the physical layout (where the surfaces are, where the sensors are mounted, what the room dimensions are). The spatial configuration is defined in a YAML file that maps physical coordinates to interaction zones:

```yaml
# spatial-config.yml
venue:
  name: "Gallery A -- Main Hall"
  dimensions: { width: 12.0, height: 4.5, depth: 8.0 }  # meters
  ambient_ir: "moderate"  # skylights present
  floor_material: "concrete"  # affects capacitive sensing

zones:
  - id: "approach"
    type: "gradient"
    bounds: { x: [0, 12], y: [0, 4.5], z: [4, 8] }
    parameters: ["visual_intensity", "audio_volume"]
    response_curve: "exponential_decay"

  - id: "intimate"
    type: "proximity"
    center: { x: 6, y: 2.25, z: 1.5 }
    radius: 2.0
    parameters: ["visual_detail", "audio_spatialization", "haptic_feedback"]
    response_curve: "linear"

  - id: "peripheral"
    type: "ambient"
    bounds: { x: [0, 12], y: [0, 4.5], z: [6, 8] }
    parameters: ["ambient_texture", "generative_seed"]
    response_curve: "slow_drift"

sensors:
  - id: "depth-main"
    type: "azure_kinect_dk"
    position: { x: 6.0, y: 4.0, z: 0.5 }
    orientation: { tilt: -15, pan: 0 }
    fov: { horizontal: 120, vertical: 120 }

  - id: "lidar-ceiling"
    type: "rplidar_a3"
    position: { x: 6.0, y: 4.5, z: 4.0 }
    orientation: { tilt: -90, pan: 0 }
    range: 25.0

  - id: "touch-surface-1"
    type: "capacitive_array"
    position: { x: 6.0, y: 1.0, z: 0.0 }
    dimensions: { width: 2.0, height: 1.5 }
    resolution: { cols: 32, rows: 24 }
```

This configuration is loaded at runtime and defines the mapping between physical space and interaction behavior. Changing the venue means editing this file, not rewriting code. The calibration procedure (documented in `docs/calibration/`) produces this file semi-automatically from sensor readings taken during setup.

### Failsafe as Aesthetic Decision

Every sensor will fail. Depth cameras lose tracking when ambient infrared overwhelms their projector. LIDAR units report garbage data when reflective surfaces produce phantom returns. Capacitive sensors drift when humidity changes. Network connections drop. Power supplies brown out. The question is not whether these failures will happen but what the installation does when they happen.

Most interactive installations handle sensor failure by going to a default state -- a static image, silence, a "please wait" message. This is a technical decision masquerading as no decision. This repository treats failsafe behavior as an aesthetic decision that the artist must make deliberately. The failsafe configuration includes three modes:

- **Graceful degradation**: The installation continues with reduced sensor data, automatically adjusting its behavior to work with fewer inputs. If the depth camera fails but LIDAR is still running, the system drops gesture and body-orientation features but maintains position tracking. The visual complexity reduces proportionally, creating a simpler but coherent experience.
- **Autonomous drift**: The installation transitions to a generative mode that does not require sensor input. The response engine continues to evolve its parameters using the last known audience state as a seed, producing slowly drifting audio-visual behavior that feels intentional rather than broken. This mode can run indefinitely and is visually coherent as a standalone experience.
- **Theatrical blackout**: The installation performs a deliberate, graceful shutdown -- lights dim, sound fades, a final visual gesture -- rather than an abrupt cut to black. This mode treats the failure as a dramatic moment and is appropriate for installations where the boundary between "working" and "not working" is part of the artistic concept.

The choice among these modes is configured per-sensor and per-zone, allowing different parts of the installation to respond differently to the same failure event.

---

## Technical Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        INSTALLATION HOST                            │
│                     (Linux workstation, GPU)                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐       │
│  │ Depth Camera │  │    LIDAR     │  │  Capacitive Touch  │       │
│  │ Azure Kinect │  │  RPLidar A3  │  │   Surface Array    │       │
│  │  (USB 3.0)   │  │  (USB 2.0)  │  │   (SPI/I2C)       │       │
│  └──────┬───────┘  └──────┬───────┘  └────────┬───────────┘       │
│         │                 │                    │                    │
│  ┌──────▼─────────────────▼────────────────────▼───────────┐       │
│  │                  SENSOR FUSION LAYER                     │       │
│  │  - Body detection + tracking (multi-sensor)              │       │
│  │  - Feature extraction (position, velocity, gesture)      │       │
│  │  - Coordinate space unification                          │       │
│  │  - Sensor health monitoring + failover                   │       │
│  │  (src/sensors/fusion.ts)                                │       │
│  └──────────────────────┬──────────────────────────────────┘       │
│                         │                                          │
│  ┌──────────────────────▼──────────────────────────────────┐       │
│  │                  RESPONSE ENGINE                         │       │
│  │  - Zone-based parameter mapping                          │       │
│  │  - Response curve interpolation                          │       │
│  │  - Multi-body interaction resolution                     │       │
│  │  - Failsafe mode management                              │       │
│  │  - Performance SDK integration (metasystem-master)       │       │
│  │  (src/engine/response.ts)                               │       │
│  └────────┬──────────────────────┬─────────────────────────┘       │
│           │                      │                                  │
│  ┌────────▼────────┐  ┌─────────▼──────────┐  ┌────────────────┐  │
│  │  VISUAL OUTPUT  │  │   AUDIO OUTPUT     │  │  HAPTIC OUTPUT │  │
│  │  - Projection   │  │  - Spatial audio   │  │  - Vibration   │  │
│  │  - LED arrays   │  │  - SuperCollider   │  │  - Air jets    │  │
│  │  - Screens      │  │  - Ambisonics      │  │  - Pneumatics  │  │
│  │  (Three.js/     │  │  (OSC bridge)      │  │  (GPIO/DMX)    │  │
│  │   GLSL)         │  │                    │  │                │  │
│  └─────────────────┘  └────────────────────┘  └────────────────┘  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                  MONITORING DASHBOARD                        │   │
│  │  - Real-time sensor status (health, latency, frame rate)    │   │
│  │  - Visitor count + heatmap                                  │   │
│  │  - System resource usage (CPU, GPU, memory)                 │   │
│  │  - Remote access for gallery technicians                    │   │
│  │  (src/dashboard/)                                           │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Repository Structure

```
example-interactive-installation/
├── src/
│   ├── sensors/
│   │   ├── depth-camera.ts        # Azure Kinect DK driver wrapper
│   │   ├── lidar.ts              # RPLidar A3 point cloud processing
│   │   ├── capacitive.ts         # Touch surface array interface
│   │   ├── fusion.ts             # Multi-sensor body tracking
│   │   └── health-monitor.ts     # Sensor status + failover logic
│   ├── engine/
│   │   ├── response.ts           # Zone-based parameter mapping
│   │   ├── zones.ts              # Spatial zone definitions
│   │   ├── curves.ts             # Response curve interpolation
│   │   ├── failsafe.ts           # Graceful degradation modes
│   │   └── multi-body.ts         # Multi-participant interaction
│   ├── output/
│   │   ├── visual/               # Three.js + GLSL shaders
│   │   ├── audio/                # SuperCollider patches + OSC bridge
│   │   └── haptic/               # GPIO/DMX control for physical output
│   ├── dashboard/
│   │   ├── server.ts             # Express + WebSocket dashboard backend
│   │   └── ui/                   # React monitoring interface
│   └── index.ts                  # Main entry point
├── config/
│   ├── spatial-config.yml        # Venue-specific spatial configuration
│   ├── sensor-defaults.yml       # Default sensor parameters
│   ├── failsafe-modes.yml        # Failsafe behavior configuration
│   └── presets/                  # Pre-built venue configurations
│       ├── small-gallery.yml
│       ├── large-museum.yml
│       └── outdoor-festival.yml
├── calibration/
│   ├── scripts/                  # Semi-automated calibration tools
│   ├── test-patterns/            # Visual calibration targets
│   └── docs/                    # Step-by-step calibration guide
├── deployment/
│   ├── hardware-bom.md          # Bill of materials with pricing
│   ├── network-diagram.md       # Network topology for installation
│   ├── power-requirements.md    # Electrical specifications
│   ├── gallery-technician.md    # Maintenance guide for venue staff
│   ├── packing-checklist.md     # Equipment transport checklist
│   └── opening-night.md        # Day-of deployment runbook
├── docs/
│   ├── architecture.md          # System design decisions
│   ├── sensor-selection.md      # Hardware comparison and rationale
│   ├── venue-assessment.md      # How to evaluate a space
│   └── failure-catalog.md       # Documented failure modes + solutions
├── docker-compose.yml            # Full stack for development
├── docker-compose.prod.yml       # Production deployment
└── package.json
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Sensor Fusion | TypeScript, Node.js 18+ | Multi-sensor body tracking |
| Depth Camera | Azure Kinect DK / Intel RealSense | Body detection + skeleton tracking |
| LIDAR | RPLidar A3 / Velodyne VLP-16 | Point cloud + proximity mapping |
| Touch Surfaces | MPR121 capacitive arrays | Pressure-sensitive touch input |
| Visual Output | Three.js + custom GLSL shaders | Real-time generative visuals |
| Audio Output | SuperCollider 3.13+ via OSC | Spatial audio synthesis |
| Performance SDK | metasystem-master | Parameter bus + consensus engine |
| Dashboard | React + Express + WebSocket | Real-time monitoring |
| Deployment | Docker Compose | Reproducible production environment |
| Host OS | Ubuntu 22.04 LTS | Stability for long-running installations |

---

## Installation

### Development Environment

```bash
# Clone the repository
git clone https://github.com/organvm-ii-poiesis/example-interactive-installation.git
cd example-interactive-installation

# Install dependencies
pnpm install

# Start in simulation mode (no hardware required)
pnpm run dev:simulated
```

Simulation mode generates synthetic sensor data -- virtual bodies moving through a virtual room -- so you can develop response behaviors and visual output without physical sensors connected. The simulated bodies follow configurable movement patterns (random walk, choreographed paths, crowd dynamics) defined in `config/simulation/`.

### Production Deployment

```bash
# Configure for your venue
cp config/presets/small-gallery.yml config/spatial-config.yml
# Edit spatial-config.yml with your venue dimensions and sensor positions

# Run calibration (requires sensors connected)
pnpm run calibrate

# Build and deploy
docker compose -f docker-compose.prod.yml up -d

# Verify all sensors are reporting
pnpm run health-check
```

### Hardware Requirements

| Component | Minimum | Recommended | Purpose |
|-----------|---------|-------------|---------|
| GPU | NVIDIA GTX 1660 | NVIDIA RTX 3070 | Visual rendering + ML inference |
| CPU | Intel i5 / AMD Ryzen 5 | Intel i7 / AMD Ryzen 7 | Sensor processing |
| RAM | 16 GB | 32 GB | Multi-sensor data buffering |
| Storage | 256 GB SSD | 512 GB NVMe | OS + logging |
| Network | Gigabit Ethernet | Gigabit Ethernet | Dashboard access |
| Depth Camera | 1x Azure Kinect DK | 2-4x for full coverage | Body tracking |
| LIDAR | 1x RPLidar A3 | 1x Velodyne VLP-16 | Point cloud |
| Audio Interface | 2-channel | 8+ channel (MOTU, RME) | Spatial audio |
| Projector | 3000 lumens, 1080p | 5000+ lumens, 4K | Visual output |

---

## Quick Start

### Simulated Installation (5 Minutes)

```bash
# Start the full stack in simulation mode
pnpm run dev:simulated

# Open the monitoring dashboard
# http://localhost:3001

# Open the visual output
# http://localhost:3000
```

The simulated installation shows five virtual participants moving through a virtual gallery. The visual output responds to their positions and velocities. The dashboard shows real-time sensor status, participant positions on a top-down map, and system performance metrics.

### Minimal Hardware Setup (30 Minutes)

```bash
# Connect one Azure Kinect DK via USB 3.0
# Place it at approximately head height (1.8m), angled down 15 degrees

# Run the single-sensor configuration
pnpm run dev:single-sensor

# Stand in front of the camera (1-4 meters)
# The visual output responds to your position and movement
```

---

## Working Examples

### Example 1: Breath of the Room

A meditative installation where the room "breathes" in response to collective visitor presence. When the room is empty, a slow ambient pulse (visual glow + low drone) cycles at approximately one breath per 8 seconds. As visitors enter, their presence accelerates the pulse. A single visitor creates gentle acceleration; a crowd creates rapid, energetic breathing. When all visitors leave, the room slowly returns to its resting state over 60 seconds.

```typescript
// examples/breath-of-the-room/response.ts
import { ResponseEngine, Zone } from '../../src/engine/response';
import { BodyTracker } from '../../src/sensors/fusion';

const engine = new ResponseEngine({
  baseBreathRate: 0.125,  // Hz (8 seconds per cycle)
  maxBreathRate: 2.0,     // Hz (0.5 seconds per cycle)
  presenceDecay: 60,      // seconds to return to rest
  zones: [
    {
      id: 'whole-room',
      type: 'ambient',
      parameters: {
        breathRate: {
          input: 'occupancy',        // number of detected bodies
          curve: 'logarithmic',      // diminishing returns per person
          range: [0.125, 2.0],
        },
        breathDepth: {
          input: 'average_velocity',  // how fast people are moving
          curve: 'linear',
          range: [0.3, 1.0],         // still crowd = shallow breath
        },
        warmth: {
          input: 'time_occupied',    // how long people have been present
          curve: 'asymptotic',       // approaches but never reaches 1.0
          range: [0.1, 0.9],
        },
      },
    },
  ],
});
```

### Example 2: Threshold

A two-zone installation where a boundary line divides the room. On one side, generative visuals respond with warm colors and harmonic tones. On the other side, the same visual algorithms run with cool colors and dissonant textures. The boundary itself is a zone of interference: visitors standing on the line create visual and sonic collisions between the two sides. The piece explores the aesthetics of borders, liminality, and the embodied experience of crossing from one state to another.

### Example 3: Congregation

An installation that responds to group formation. When visitors spread out, the audio-visual environment is sparse and individual -- each person has their own sonic territory and visual halo. When visitors cluster together (group density exceeds a threshold), the individual elements merge into a collective audiovisual entity that none of them would produce alone. The piece rewards gathering and shared proximity, producing emergent collective aesthetics that no single participant controls.

---

## Theory Implemented

### Phenomenology of Interaction

The sensing and response design draws on Maurice Merleau-Ponty's phenomenology of perception: the body is not an object in space but the means by which space is experienced. The multi-feature sensing pipeline (position, velocity, orientation, gesture, proximity, touch, group density) attempts to capture what Merleau-Ponty called the "motor intentionality" of the body -- the way bodies project purpose into space through movement, not just through conscious decision. The response engine maps these features to audio-visual parameters through continuous gradients, not discrete triggers, because embodied experience is continuous, not discrete.

### Relational Aesthetics

Nicolas Bourriaud's concept of relational aesthetics -- art as the production of human relationships rather than objects -- informs the multi-body interaction design. The installation is not optimized for a single visitor. It is designed for groups, and its most interesting behaviors emerge from the spatial relationships between multiple bodies. Two visitors approaching each other produce an acoustic convergence. Three visitors forming a triangle create a visual resonance pattern. A crowd produces emergent collective behavior that no individual intended. The art is not the visuals or the sound -- it is the social choreography that the installation reveals and amplifies.

### Cybernetic Feedback

The installation creates a cybernetic loop: visitors move, the installation responds, the response influences how visitors move, which changes the installation's response. This is second-order cybernetics applied to spatial interaction -- the system and its participants are mutually constitutive. The failsafe modes (graceful degradation, autonomous drift, theatrical blackout) are themselves cybernetic design decisions: they determine how the system responds when part of its feedback loop is severed.

---

## Portfolio & Exhibition

### For Grant Reviewers

This repository demonstrates:

- **Technical depth** in real-time sensor fusion, spatial computing, and multi-modal output
- **Exhibition readiness**: complete deployment documentation including hardware procurement, venue assessment, calibration, and maintenance
- **Artistic rigor**: failsafe behavior treated as aesthetic decision, not merely technical necessity
- **Scalability**: configurable from a single-sensor studio prototype to a multi-sensor museum-scale installation
- **Reproducibility**: any artist can adapt this reference implementation for their own installation concepts

### For Curators and Venues

The `deployment/` directory contains everything a gallery technician needs to maintain the installation after the artist has left: daily startup/shutdown procedures, troubleshooting guides for common sensor issues, contact information for emergency support, and a packing checklist for de-installation. The monitoring dashboard provides remote access so the artist can check on the installation from anywhere.

### For Hiring Managers

This repository demonstrates expertise in: real-time systems engineering, sensor fusion and computer vision, spatial computing and interaction design, production deployment for non-traditional computing environments, and technical documentation for non-technical stakeholders (gallery staff, curators).

---

## Related Work

- **Random International, "Rain Room" (2012)**: Sensor-driven installation where rain stops falling wherever visitors stand. Pioneered large-scale body-tracking in installation contexts. Example Interactive Installation extends this approach with multi-feature sensing and continuous (rather than binary) response.
- **teamLab, "Borderless" (2018-present)**: Immersive digital art museum with installations that respond to visitor presence and flow between rooms. Example Interactive Installation provides the open-source infrastructure for similar sensor-driven spatial interactions.
- **Rafael Lozano-Hemmer, "Pulse Room" (2006)**: Heart-rate sensors drive incandescent light bulbs. Demonstrates the power of mapping intimate biometric data to environmental response. Example Interactive Installation extends the sensing vocabulary beyond biometrics to full-body spatial tracking.
- **Ryoji Ikeda, "test pattern" (2008-present)**: Data-driven audiovisual installation series. Demonstrates the aesthetic power of high-frame-rate, high-resolution audio-visual synchronization. Example Interactive Installation inherits this precision while adding real-time interactivity.
- **Camille Utterback and Romy Achituv, "Text Rain" (1999)**: Early interactive installation where falling text responds to body silhouettes captured by camera. A foundational work in camera-based interaction that Example Interactive Installation builds upon with contemporary sensing technology.

### Cross-References Within the Eight-Organ System

| Repository | Organ | Relationship |
|-----------|-------|-------------|
| [metasystem-master](https://github.com/organvm-ii-poiesis/metasystem-master) | II | Performance SDK provides parameter bus and consensus engine |
| [learning-resources](https://github.com/organvm-ii-poiesis/learning-resources) | II | Tier 3 capstone uses this as reference implementation |
| [example-ai-collaboration](https://github.com/organvm-ii-poiesis/example-ai-collaboration) | II | AI-driven generative modes for autonomous drift failsafe |
| [recursive-engine](https://github.com/organvm-i-theoria/recursive-engine) | I | Recursive generative algorithms used in visual output |
| [agentic-titan](https://github.com/organvm-iv-taxis/agentic-titan) | IV | Orchestration patterns for multi-sensor coordination |

---

## Contributing

### How to Contribute

```bash
# Fork and clone
git clone https://github.com/<your-fork>/example-interactive-installation.git
cd example-interactive-installation
pnpm install

# Create a feature branch
git checkout -b feature/your-feature-name

# Make changes, run tests
pnpm test
pnpm run lint

# Commit (conventional commits)
git commit -m "feat(sensors): add Intel RealSense D455 driver"

# Push and open a PR
git push origin feature/your-feature-name
```

### Contributions Especially Welcome

- **Sensor drivers**: Drivers for additional depth cameras (Intel RealSense, Stereolabs ZED), LIDAR units, or novel input devices
- **Venue presets**: Spatial configurations for specific venue types (black box theatre, outdoor amphitheatre, storefront window)
- **Response behaviors**: New response algorithms for the engine (particle systems, fluid simulations, neural style transfer)
- **Deployment guides**: Installation documentation for specific operating systems, cloud platforms, or edge computing devices
- **Failure reports**: If you deployed this system and something went wrong, document what happened and how you fixed it. The failure catalog is the most valuable part of this repository.

---

## License & Author

**License:** [MIT](LICENSE)

**Author:** Anthony Padavano ([@4444J99](https://github.com/4444J99))

**Organization:** [organvm-ii-poiesis](https://github.com/organvm-ii-poiesis) (ORGAN-II: Poiesis)

**System:** [meta-organvm](https://github.com/meta-organvm) -- the eight-organ creative-institutional system coordinating ~80 repositories across theory, art, commerce, orchestration, public process, community, and marketing.

---

<sub>This README is a Gap-Fill Sprint portfolio document for the organvm system. It is written for grant reviewers, curators, and collaborators who want to understand what this reference implementation provides, how it handles the realities of exhibition deployment, and how it fits within a larger creative-institutional architecture.</sub>