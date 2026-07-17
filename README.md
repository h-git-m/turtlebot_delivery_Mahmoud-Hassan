# turtlebot_delivery_Mahmoud-Hassan

https://github.com/user-attachments/assets/c9beddb1-0e6b-4f87-9267-cbb3af3c71cb

## 1. Step-by-Step Setup Instructions
1. Add `delivery_mission_controller` and `delivery_mission_interfaces` packages to the `src` folder of your ROS2 workspace.
2. Open a terminal and navigate to your workspace root (e.g., from a nested folder, go back two levels).
3. Source your shell configuration to load ROS2 environment variables.
4. Build only the added packages.
5. Source the newly built workspace so ROS2 can find the package's executables.
6. Verify the package's executables are available.
7. In the 3D simulator, launch `turtlebot3_world.launch` to load the robot environment.
8. Run the delivery_mission_node found in `delivery_mission_controller` to start the delivery simulation action server and keep it on standby for a client request. 
9. Open a new terminal and repeat steps 2, 3, and 5 to set up the environment there too.
10. Run the delivery_mission_client found in `delivery_mission_controller` to send the delivery simulation action client requests to the initalized server in step 8. 
11. Open a third terminal, source the environment, and run `rqt_graph` to visualize the running ROS2 nodes/topics, if needed.

## 2. Commands Used and What They Do
| Command | Description |
|---|---|
| `cd ../..` | Moves up two directory levels, back to the workspace root. |
| `source ~/.bashrc` | Reloads shell configuration, ensuring ROS2 environment variables are set. |
| `colcon build --packages-select delivery_mission_controller delivery_mission_interfaces` | Builds only these packages instead of the whole workspace. |
| `source install/setup.bash` | Loads the newly built package into the current terminal's environment so ROS2 can find it. |
| `ros2 pkg executables delivery_mission_controller` | Lists all runnable executables (nodes) inside the `delivery_mission_controller` package. |
| `ros2 run delivery_mission_controller delivery_mission_server` | Runs the delivery_mission_node to start the delivery simulation action server and keep it on standby for a client request. Upon client request, this node will be sending `Twist` messages to `/cmd_vel` topic|
| `ros2 run delivery_mission_controller delivery_mission_client --speed 0.2 --pickup_dur 5 --delivery_dur 5 --timeout 20` | Sends the delivery simulation action client request to the initalized server in step 8|
| `ros2 action send_goal /delivery_mission delivery_mission_interfaces/action/DeliveryMission "{speed: 0.2, pickup_dur: 5, delivery_dur: 5.0, timeout: 20.0}" --feedback` | Another method that sends the delivery simulation action client request to the initalized server in step 8. However, it doesn't stop with keyboard interrupts such as ctrl+c|
| `ros2 run rqt_graph rqt_graph` | Opens a graphical tool showing active nodes and topic connections in the ROS2 system. |

## 3. How to Test the Nodes
1. Launch the simulator with `turtlebot3_world.launch` to load the robot.
2. In Terminal 1: run `ros2 run delivery_mission_controller delivery_mission_server` and observe the delivery simulation action server acknowledging commencement.
3. In Terminal 2 (after sourcing the workspace again): run `ros2 run delivery_mission_controller delivery_mission_client --speed 0.2 --pickup_dur 5 --delivery_dur 5 --timeout 20` Update the passed arguments according to the delivery mission required and to test different scenarios such as cancelling the delivery or exceeding delivery timeout.
4. Watch the robot in the simulator to confirm its movement matches the requested client request and observe all terminals outputs from goal acknowledgment to feedback printing to final Results and Goal fullfilment.

## 4. Expected Output

Example run: `ros2 run delivery_mission_controller delivery_mission_client --speed 0.2 --pickup_dur 5 --delivery_dur 5 --timeout 20`

1. **Terminal 1 (`delivery_mission_server` node):**
   - On startup, logs `Delivery Mission Server Started`.
   - On receiving a request, logs the accepted goal, e.g.:
     
[INFO] [delivery_mission_server]: GOAL ACCEPTED: speed=0.20 pickup_dur=5.00 delivery_dur=5.00 timeout=20.00

   - **Phase 1 (drive to pickup)** — logs each tick while driving forward, e.g.:
     
[INFO] [delivery_mission_server]: PHASE 1: driving forward to pickup location
 [INFO] [delivery_mission_server]: PHASE 1: elapsed=0.25s remaining=4.75s

   - **Phase 2 (simulate pickup)** — robot stops, logs progress toward pickup completion, e.g.:
     
[INFO] [delivery_mission_server]: PHASE 2: stopped - simulating pickup
 [INFO] [delivery_mission_server]: PHASE 2: picking up, remaining=1.50s
 [INFO] [delivery_mission_server]: PHASE 2: package secured

   - **Phase 3 (drive to delivery)** — logs each tick while driving backward, e.g.:
     
[INFO] [delivery_mission_server]: PHASE 3: driving backward to deliver package
 [INFO] [delivery_mission_server]: PHASE 3: elapsed=0.25s remaining=4.75s

   - On successful completion, logs:
     
[INFO] [delivery_mission_server]: MISSION COMPLETED

   - If a cancel request arrives mid-mission, logs a warning and stops the robot immediately, e.g.:
     
[WARN] [delivery_mission_server]: CANCEL REQUEST received
 [WARN] [delivery_mission_server]: MISSION CANCELED during PHASE 1 (drive to pickup)

   - If the total elapsed time exceeds `timeout` before the mission finishes, the server aborts and stops the robot, e.g. (running with `--timeout 6`, which is shorter than the ~7s needed to finish pickup):
     
[ERROR] [delivery_mission_server]: MISSION ABORTED (timeout) during PHASE 2 (pickup)

2. **Terminal 2 (`delivery_mission_client` node):**
   - Logs the goal being sent and the server's acknowledgment, e.g.:
     
[INFO] [delivery_mission_client]: SENDING GOAL: speed=0.20 pickup_dur=5.00 delivery_dur=5.00 timeout=20.00
 [INFO] [delivery_mission_client]: GOAL ACCEPTED by server

   - Prints feedback as it streams in from each phase, e.g.:
     
[INFO] [delivery_mission_client]: FEEDBACK [pickup] elapsed=0.25s remaining=4.75s | Driving to pickup location...
 [INFO] [delivery_mission_client]: FEEDBACK [pickup] elapsed=5.50s remaining=1.50s | Picking up package... 1.5s left
 [INFO] [delivery_mission_client]: FEEDBACK [pickup] elapsed=7.00s remaining=0.00s | Package secured!
 [INFO] [delivery_mission_client]: FEEDBACK [delivery] elapsed=0.25s remaining=4.75s

   - On success, prints the final result, e.g.:
     
[INFO] [delivery_mission_client]: MISSION SUCCEEDED: Delivery mission completed (pickup 5.00s, delivery 5.00s)

   - On a `--timeout 6` run, prints the abort result instead, e.g.:
     
[WARN] [delivery_mission_client]: MISSION FAILED: Mission aborted: timeout exceeded during PHASE 2 (pickup) (status=6)

   - If `Ctrl+C` is pressed, the client sends a cancel request before shutting down, and the server's `MISSION CANCELED` log confirms the robot was stopped.

3. **Simulator (Gazebo/turtlebot3_world):**
   - The robot drives straight forward at `speed` m/s for `pickup_dur` seconds.
   - The robot then stops in place for ~2 seconds while the pickup is simulated.
   - The robot then drives straight backward at `speed` m/s for `delivery_dur` seconds, retracing its path to the delivery point.
   - If the mission is canceled or times out at any point, the robot halts immediately (zero `Twist` published) instead of continuing to the next phase.

4. **Terminal 3 (`rqt_graph`):**
   - A graph window opens showing:
     - `/delivery_mission_server` node connected to `/cmd_vel` (publisher).
     - The `/delivery_mission` action links (goal, cancel, feedback, result, status) between the client node (or the `ros2 action send_goal` CLI) and `/delivery_mission_server`.
   - Confirms the node is correctly wired to the simulator's `/cmd_vel` topic with no disconnected nodes.
