import numpy


def get_next_environment_id(next_environment_id_to_prob):
    probs = list(next_environment_id_to_prob.values())
    environments = list(next_environment_id_to_prob)
    return numpy.random.choice(environments, p=probs)


def select_interaction(patient, environment, patient_time, interaction_mapper):
    for i in range(15):
        interaction_name = numpy.random.choice(environment.interactions)
        if interaction_name == "death":
            continue
    return interaction_name, interaction_mapper[interaction_name]


def intelligence(patient, environment, patient_time, interaction_mapper):

    interaction_name, interaction = select_interaction(
        patient, environment, patient_time, interaction_mapper
    )
    # print(
    #     f"{datetime.datetime.now()} - Inside intelligence layer:\n"
    #     f"patient_name: {patient.name}\n"
    #     f"patient_time: {patient_time}\n"
    #     f"environment_name: {environment.name}\n"
    #     f"interaction_name: {interaction_name}\n"
    # )

    (
        patient,
        environment,
        update_data,
        next_environment_id_to_prob,
        next_environment_id_to_time,
    ) = interaction(patient, environment, patient_time)

    if len(next_environment_id_to_prob) > 0:
        next_environment_id = get_next_environment_id(
            next_environment_id_to_prob
        )
    else:
        next_environment_id = None

    if len(next_environment_id_to_prob) > 0:
        patient_time = (
            patient_time + next_environment_id_to_time[next_environment_id]
        )

    interaction_names = [interaction_name]
    return (
        patient,
        environment,
        patient_time,
        update_data,
        next_environment_id,
        interaction_names,
        next_environment_id_to_prob,
        next_environment_id_to_time,
    )
