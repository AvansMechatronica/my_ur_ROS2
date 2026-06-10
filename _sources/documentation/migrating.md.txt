# Een andere UR-type robot configureren.

Met de migratie tool kan de template geschikt gemaakt worden voor een ander type Universal Robots robot.
Beschikare robots zijn: `ur3`, `ur5`, `ur10`, `ur3e`, `ur5e`, `ur7e`, `ur10e`, `ur12e`, `ur16e`, `ur8long`, `ur15`, `ur18`, `ur20` en `ur30`.

```bash
cd ~/<workspace>/src/my_ur_ROS2/migrate/
./migrate.bash <old_type> <new_type>
```

Voorbeeld:
Migratie van `ur5` naar `ur10e`
Standaard is de template ingesteld op een `ur5` robot.
```
cd ~/<workspace>/src/my_ur_ROS2/migrate/
./migrate.bash ur5 ur10e
```

> Deze migratie is `expirimental` dus alle functionaliteit zal getest moeten worden.