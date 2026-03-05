import asyncio
from asyncua import Client, Node
import sys

# Replace with the actual compressor IP if passed as argument
SERVER_IP = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.100"
SERVER_URL = f"opc.tcp://{SERVER_IP}:4840"

async def explore_node(node: Node, level: int = 0, max_level: int = 3):
    """Recursively browses the OPC-UA server namespace to print Node IDs and Names."""
    if level > max_level:
        return

    indent = "    " * level
    try:
        # Get node details
        node_class = await node.read_node_class()
        node_name = (await node.read_browse_name()).Name
        node_id = str(node.nodeid)
        
        # Read value if it's a variable
        value_str = ""
        if str(node_class) == "NodeClass.Variable":
            try:
                val = await node.read_value()
                value_str = f" = {val}"
            except Exception:
                value_str = " = <unreadable>"

        print(f"{indent}- [{node_class.name}] {node_name} (ID: {node_id}){value_str}")

        # Recursively browse children
        children = await node.get_children()
        for child in children:
            await explore_node(child, level + 1, max_level)
            
    except Exception as e:
        print(f"{indent}- <Error reading node: {e}>")

async def main():
    print(f"Attempting to connect to OPC-UA Server at {SERVER_URL}...")
    client = Client(url=SERVER_URL)
    
    try:
        await client.connect()
        print("Connected successfully!\n")
        
        # Browse from the root node
        root = client.nodes.root
        print("Exploring OPC-UA Namespace (Max Depth: 3)...")
        await explore_node(root, level=0, max_level=3)

    except Exception as e:
        print(f"\nFailed to connect or browse: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
