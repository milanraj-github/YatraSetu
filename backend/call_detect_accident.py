import re

with open("app/services/tracking_service.py", "r") as f:
    content = f.read()

# In ingest_gps_ping:
ping_search = """                deviation_state = await detect_route_deviation(
                    db, session, bus_id, driver_user.id,
                    ping_data.latitude, ping_data.longitude,
                    ping_data.accuracy, recorded_at_naive
                )
                new_state["deviation_status"] = deviation_state
                await set_redis_json(redis_key, new_state)"""
                
ping_replace = ping_search + """
                
                # Phase 9: Accident Detection
                await detect_potential_accident(
                    db, session, bus_id, driver_user.id,
                    ping_data, recorded_at_naive, f"trip:{session.id}:accident"
                )"""

content = content.replace(ping_search, ping_replace)

# In ingest_gps_batch:
batch_search = """                    deviation_state = await detect_route_deviation(
                        db, latest_session, bus_id, driver_user.id,
                        latest_ping_data.latitude, latest_ping_data.longitude,
                        latest_ping_data.accuracy, latest_ping_time
                    )
                    new_state["deviation_status"] = deviation_state
                    await set_redis_json(redis_key, new_state)"""

batch_replace = batch_search + """
                    
                    # Phase 9: Accident Detection
                    await detect_potential_accident(
                        db, latest_session, bus_id, driver_user.id,
                        latest_ping_data, latest_ping_time, f"trip:{latest_session.id}:accident"
                    )"""
                    
content = content.replace(batch_search, batch_replace)

with open("app/services/tracking_service.py", "w") as f:
    f.write(content)
