#!/usr/bin/env python3

import time

import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

from geometry_msgs.msg import Twist

from delivery_mission_interfaces.action import DeliveryMission


class DeliveryMissionServer(Node):

    # Fixed duration (s) used to simulate the stationary "pickup" action
    # (the DeliveryMission.action goal has no dedicated field for it).
    PICKUP_SIM_SECONDS = 2.0
    RATE_HZ = 4.0

    def __init__(self):
        super().__init__('delivery_mission_server')

        # Publisher
        self.velocity_publisher = self.create_publisher(
            Twist,
            '/cmd_vel',
            10
        )

        # Let execute_callback run concurrently with goal_callback / cancel_callback
        self._callback_group = ReentrantCallbackGroup()

        # Action server
        self.mission_action_server = ActionServer(
            self,
            DeliveryMission,
            '/delivery_mission',
            execute_callback=self.execute_mission_callback,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
            callback_group=self._callback_group,
        )

        # Mission state
        self.mission_active = False

        self.get_logger().info('Delivery Mission Server Started')

    # ------------------------------------------------------------------ #
    # Goal / cancel acceptance
    # ------------------------------------------------------------------ #
    def goal_callback(self, goal_request):
        """Accept or reject an incoming goal before execution starts."""

        if self.mission_active:
            self.get_logger().warn('REJECTED: a mission is already running')
            return GoalResponse.REJECT

        if goal_request.timeout <= 0.0:
            self.get_logger().warn('REJECTED: timeout must be greater than 0')
            return GoalResponse.REJECT

        if goal_request.pickup_dur < 0.0 or goal_request.delivery_dur < 0.0:
            self.get_logger().warn('REJECTED: pickup_dur / delivery_dur must be >= 0')
            return GoalResponse.REJECT

        self.get_logger().info(
            f'GOAL ACCEPTED: speed={goal_request.speed:.2f} '
            f'pickup_dur={goal_request.pickup_dur:.2f} '
            f'delivery_dur={goal_request.delivery_dur:.2f} '
            f'timeout={goal_request.timeout:.2f}'
        )
        return GoalResponse.ACCEPT

    def cancel_callback(self, goal_handle):
        """Allow the client to cancel a running mission."""

        self.get_logger().warn('CANCEL REQUEST received')
        return CancelResponse.ACCEPT

    # ------------------------------------------------------------------ #
    # Execution
    # ------------------------------------------------------------------ #
    def execute_mission_callback(self, goal_handle):
        """Run the delivery mission: drive to pickup, pick up, drive to deliver."""

        speed = goal_handle.request.speed
        pickup_dur = goal_handle.request.pickup_dur
        delivery_dur = goal_handle.request.delivery_dur
        timeout = goal_handle.request.timeout

        self.mission_active = True
        feedback_msg = DeliveryMission.Feedback()
        result = DeliveryMission.Result()

        mission_start = time.time()
        sleep_duration = 1.0 / self.RATE_HZ

        def mission_timed_out():
            return (time.time() - mission_start) >= timeout

        def check_cancel_or_timeout(phase_name):
            """Returns a populated Result if the mission must stop early, else None."""
            if goal_handle.is_cancel_requested:
                self._publish_stop()
                goal_handle.canceled()
                result.success = False
                result.message = f'Mission canceled by client during {phase_name}'
                self.mission_active = False
                self.get_logger().warn(f'MISSION CANCELED during {phase_name}')
                return result

            if mission_timed_out():
                self._publish_stop()
                goal_handle.abort()
                result.success = False
                result.message = f'Mission aborted: timeout exceeded during {phase_name}'
                self.mission_active = False
                self.get_logger().error(f'MISSION ABORTED (timeout) during {phase_name}')
                return result

            return None

        # ---------------- PHASE 1: drive forward to pickup ---------------- #
        self.get_logger().info('PHASE 1: driving forward to pickup location')
        phase_start = time.time()
        while True:
            early_result = check_cancel_or_timeout('PHASE 1 (drive to pickup)')
            if early_result is not None:
                return early_result

            elapsed = time.time() - phase_start
            if elapsed >= pickup_dur:
                break

            cmd = Twist()
            cmd.linear.x = speed
            cmd.angular.z = 0.0
            self.velocity_publisher.publish(cmd)

            feedback_msg.elapsed_time_pick = elapsed
            feedback_msg.remaining_time_pick = max(0.0, pickup_dur - elapsed)
            feedback_msg.message_picked = 'Driving to pickup location...'
            goal_handle.publish_feedback(feedback_msg)

            self.get_logger().info(
                f'PHASE 1: elapsed={elapsed:.2f}s remaining={pickup_dur - elapsed:.2f}s'
            )
            time.sleep(sleep_duration)

        self._publish_stop()

        # ---------------- PHASE 2: stop and simulate pickup ---------------- #
        self.get_logger().info('PHASE 2: stopped - simulating pickup')
        phase_start = time.time()
        while True:
            early_result = check_cancel_or_timeout('PHASE 2 (pickup)')
            if early_result is not None:
                return early_result

            elapsed = time.time() - phase_start
            if elapsed >= self.PICKUP_SIM_SECONDS:
                break

            remaining = max(0.0, self.PICKUP_SIM_SECONDS - elapsed)
            feedback_msg.elapsed_time_pick = pickup_dur + elapsed
            feedback_msg.remaining_time_pick = remaining
            feedback_msg.message_picked = f'Picking up package... {remaining:.1f}s left'
            goal_handle.publish_feedback(feedback_msg)

            self.get_logger().info(f'PHASE 2: picking up, remaining={remaining:.2f}s')
            time.sleep(sleep_duration)

        feedback_msg.elapsed_time_pick = pickup_dur + self.PICKUP_SIM_SECONDS
        feedback_msg.remaining_time_pick = 0.0
        feedback_msg.message_picked = 'Package secured!'
        goal_handle.publish_feedback(feedback_msg)
        self.get_logger().info('PHASE 2: package secured')

        # ---------------- PHASE 3: drive backward to deliver ---------------- #
        self.get_logger().info('PHASE 3: driving backward to deliver package')
        phase_start = time.time()
        while True:
            early_result = check_cancel_or_timeout('PHASE 3 (deliver)')
            if early_result is not None:
                return early_result

            elapsed = time.time() - phase_start
            if elapsed >= delivery_dur:
                break

            cmd = Twist()
            cmd.linear.x = -speed
            cmd.angular.z = 0.0
            self.velocity_publisher.publish(cmd)

            feedback_msg.elapsed_time_deliv = elapsed
            feedback_msg.remaining_time_deliv = max(0.0, delivery_dur - elapsed)
            goal_handle.publish_feedback(feedback_msg)

            self.get_logger().info(
                f'PHASE 3: elapsed={elapsed:.2f}s remaining={delivery_dur - elapsed:.2f}s'
            )
            time.sleep(sleep_duration)

        self._publish_stop()
        goal_handle.succeed()
        result.success = True
        result.message = (
            f'Delivery mission completed '
            f'(pickup {pickup_dur:.2f}s, delivery {delivery_dur:.2f}s)'
        )
        self.mission_active = False
        self.get_logger().info('MISSION COMPLETED')
        return result

    def _publish_stop(self):
        cmd = Twist()
        cmd.linear.x = 0.0
        cmd.angular.z = 0.0
        self.velocity_publisher.publish(cmd)


def main(args=None):
    rclpy.init(args=args)
    server = DeliveryMissionServer()

    executor = MultiThreadedExecutor()
    executor.add_node(server)

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        server.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
