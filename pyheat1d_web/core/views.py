import json
from functools import partial
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render, resolve_url
from pyheat1d.controllers import run as run_simulation_cli
from pyheat1d.singleton import Singleton

from .forms import EditSimulationForm, NewSimulationForm
from .models import Simulation


def _get_simulations_base_folder():
    return Path(settings.MEDIA_ROOT)


def _create_or_update_simulation_case(new_case, indent=2, update=False):
    bcs = {
        "lbc": {"type": 1, "params": {"value": new_case.pop("lbc_value")}},
        "rbc": {"type": 1, "params": {"value": new_case.pop("rbc_value")}},
    }

    props = {"k": 1.0, "ro": 1.0, "cp": 1.0}

    new_case.update(bcs)
    new_case.update({"prop": props, "write_every_steps": 100})

    tag = new_case.pop("tag")
    base_folder = _get_simulations_base_folder()

    if not update:
        simulation_folder = base_folder / tag
        if not simulation_folder.exists():
            simulation_folder.mkdir()

    case_file = base_folder / f"{tag}/case.json"

    # TODO: trata a exceção
    json.dump(new_case, case_file.open(mode="w"), indent=indent)

    return case_file


def create_simulation_form(request):
    if request.method == "POST":
        form = NewSimulationForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Erro na hora da criação da simulação.")
            return render(
                request,
                "core/create_simulation_form.html",
                context={"form": form},
            )

        form.instance.input_file = _create_or_update_simulation_case(form.cleaned_data.copy())

        form.save()

        return HttpResponseRedirect(resolve_url("core:list_simulation"))
    else:
        form = NewSimulationForm()

    return render(request, "core/create_simulation_form.html", context={"form": form})


def run_simulation(request, pk):
    sim = Simulation.objects.get(id=pk)
    sim.status = Simulation.Status.RUNNING
    sim.save()
    try:
        Singleton._instances = {}  # TODO: Gambirra para pode fazer funcionar
        run_simulation_cli(input_file=Path(sim.input_file))
    except Exception as e:
        messages.error(request, e)
        print(e)  # #TODO: logar
        sim.status = Simulation.Status.FAILED
    else:
        sim.status = Simulation.Status.SUCCESS
    finally:
        sim.save()

    return HttpResponseRedirect(resolve_url("core:list_simulation"))


def list_simulation(request):
    sim = Simulation.objects.all()
    return render(request, "core/list_simulation.html", context={"analysis": sim})


def _recover_info_detail_from_db(sim):
    data = {
        "Id": sim.pk,
        "Tag": sim.tag,
        "Arquivo de entrada": sim.input_file,
        "Status": sim.get_status_display(),
    }

    temporal_dist = {"Delta t": sim.dt, "Passos de tempo": sim.nstep}

    geom = {"Comprimento": sim.length, "Divisões": sim.ndiv}

    bcs = {"Esquerda": sim.lbc_value, "Direita": sim.rbc_value}

    initial_conditions = {"Temperatuta Inicial": sim.initialt}
    return {
        "data": data,
        "bcs": bcs,
        "geom": geom,
        "temporal_dist": temporal_dist,
        "initial_conditions": initial_conditions,
    }


def detail_simulation(request, pk):
    sim = Simulation.objects.get(id=pk)

    context = _recover_info_detail_from_db(sim)

    return render(request, "core/detail_simulation.html", context=context)


def _delete_simulation_folder(input_file):
    if input_file.exists():
        input_file.unlink()

    base_dir = input_file.parent

    mesh_file = base_dir / "mesh.json"
    if mesh_file.exists():
        mesh_file.unlink()

    results_file = base_dir / "results.json"
    if results_file.exists():
        results_file.unlink()

    base_dir.rmdir()


def delete_simulation(request, pk):
    url_out = resolve_url("core:list_simulation")

    try:
        sim = Simulation.objects.get(id=pk)
    except Simulation.DoesNotExist:
        messages.error(request, f"Simulação com {id} não foi encontrada.")
        return HttpResponseRedirect(url_out)

    try:
        _delete_simulation_folder(Path(sim.input_file))
    except OSError:  # TODO: Criar um exeção personalizadas
        messages.error(request, f"Não foi possivel deletar o diretório da Simulação {sim.tag}.")
        return HttpResponseRedirect(url_out)

    sim.delete()

    return HttpResponseRedirect(url_out)


# TODO: limitar ao metodo GET
def get_simulation_results_api(request, pk):
    sim = Simulation.objects.get(id=pk)

    input_file = Path(sim.input_file)

    base_dir = input_file.parent

    graphs = {}

    if sim.status == Simulation.Status.SUCCESS:
        mesh_file = base_dir / "mesh.json"
        mesh = json.load(mesh_file.open())
        results_file = base_dir / "results.json"
        results = json.load(results_file.open())

        graphs["mesh"] = list(map(partial(round, ndigits=2), mesh["xp"]))
        graphs["steps"] = [
            {
                "step": results[i]["istep"],
                "t": round(results[i]["t"], 2),
                "u": results[i]["u"],
            }
            for i in [0, 1, -1]
        ]

    return JsonResponse(graphs)


def results_simulation(request, pk):
    return render(request, "core/results_simulation.html", context={"id": pk})


def edit_simulation_form(request, pk):
    sim = get_object_or_404(Simulation, id=pk)

    if request.method == "POST":
        form = EditSimulationForm(request.POST, instance=sim)

        if not form.is_valid():
            messages.error(request, "Erro na hora da criação da simulação.")
            return render(
                request,
                "core/create_simulation_form.html",
                context={"form": form},
            )
        form.instance.status = Simulation.Status.INIT
        form.save()

        case_data = {**form.cleaned_data.copy(), "tag": sim.tag}
        _create_or_update_simulation_case(case_data, update=True)
        messages.success(request, f"Dados da simulação atualizados {sim.tag}")
        return HttpResponseRedirect(resolve_url("core:list_simulation"))
    else:
        form = EditSimulationForm(instance=sim)

    return render(request, "core/edit_simulation_form.html", context={"form": form, "tag": sim.tag})
