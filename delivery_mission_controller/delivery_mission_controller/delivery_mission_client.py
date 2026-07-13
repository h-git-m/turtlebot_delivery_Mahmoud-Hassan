#!/usr/bin/env python3

import argparse
import sys

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from delivery_mission_interfaces.action import DeliveryMission


class DeliveryMissionClient(Node):

    def __init__(self):
        super().__init__('delivery_mission_client')
        self._action_client = ActionClient(self, DeliveryMission, '/delivery_mission')
        self._goal_handle = None

    def send_goal(self, speed, pickup_dur, delivery_dur, timeout):
        self.get_logger().info('Waiting for /delivery_mission action server...')
        self._action_client.wait_for_server()

        goal_msg = DeliveryMission.Goal()
        goal_msg.speed = speed
        goal_msg.pickup_dur = pickup_dur
        goal_msg.delivery_dur = delivery_dur
        goal_msg.timeout = timeout

        self.get_logger().info(
            f'SENDING GOAL: speed={speed:.2f} pickup_dur={pickup_dur:.2f} '
            f'delivery_dur={delivery_dur:.2f} timeout={timeout:.2f}'
        )

        send_goal_future = self._action_client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_callback
        )
        send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()

        if not goal_handle.accepted:
            self.get_logger().warn('GOAL REJECTED by server')
            rclpy.shutdown()
            return

        self.get_logger().info('GOAL ACCEPTED by server')
        self._goal_handle = goal_handle

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.get_result_callback)

    def feedback_callback(self, feedback):
        fb = feedback.feedback

        if fb.message_picked:
            self.get_logger().info(
                f'FEEDBACK [pickup] elapsed={fb.elapsed_time_pick:.2f}s '
                f'remaining={fb.remaining_time_pick:.2f}s | {fb.message_picked}'
            )

        if fb.elapsed_time_deliv > 0.0 or fb.remaining_time_deliv > 0.0:
            self.get_logger().info(
                f'FEEDBACK [delivery] elapsed={fb.elapsed_time_deliv:.2f}s '
                f'remaining={fb.remaining_time_deliv:.2f}s'
            )

    def get_result_callback(self, future):
        result = future.result().result
        status = future.result().status

        if result.success:
            self.get_logger().info(f'MISSION SUCCEEDED: {result.message}')
        else:
            self.get_logger().warn(f'MISSION FAILED: {result.message} (status={status})')

        rclpy.shutdown()

    def cancel_goal(self):
        if self._goal_handle is not None:
            self.get_logger().warn('Sending CANCEL request')
            self._goal_handle.cancel_goal_async()


def main(args=None):
    parser = argparse.ArgumentParser(description='Delivery Mission action client')
    parser.add_argument('--speed', type=float, default=0.2, help='Forward/backward speed (m/s)')
    parser.add_argument('--pickup_dur', type=float, default=5.0, help='Drive-to-pickup duration (s)')
    parser.add_argument('--delivery_dur', type=float, default=5.0, help='Drive-to-delivery duration (s)')
    parser.add_argument('--timeout', type=float, default=30.0, help='Total mission timeout (s)')
    parsed_args, remaining = parser.parse_known_args(args=sys.argv[1:])

    rclpy.init(args=remaining)
    client = DeliveryMissionClient()
    client.send_goal(
        parsed_args.speed,
        parsed_args.pickup_dur,
        parsed_args.delivery_dur,
        parsed_args.timeout
    )

    try:
        rclpy.spin(client)
    except KeyboardInterrupt:
        client.cancel_goal()
    finally:
        client.destroy_node()


if __name__ == '__main__':
    main()
