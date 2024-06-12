class TargetTrigger:
    def __init__(
        self,
        id_nr,
        name,
        team,
        source_target_id,
        dest_target_id,
        dist_to_poi,
        poi_id_nr,
    ):
        self.id_nr = id_nr
        name = name.replace("<br>", "")
        self.name = name
        self.team = team
        self.source_target_id = source_target_id
        self.dest_target_id = dest_target_id
        self.dist_to_poi = dist_to_poi
        self.poi_id_nr = poi_id_nr

    def __str__(self):  # printing function
        return (
            "<Trigger id:%s name:%s source_targ:%s dest_targ:%s dist_to_poi:%s poi_id_nr:%s >"
            % (
                self.id_nr,
                self.name,
                self.source_target_id,
                self.dest_target_id,
                self.dist_to_poi,
                self.poi_id_nr,
            )
        )


def to_trigger_params(dct):
    return TargetTrigger(
        dct["id"],
        dct["name"],
        "unknown",
        dct["source_target_id"],
        dct["dest_target_id"],
        dct["dist_to_poi"],
        dct["poi_id_nr"],
    )